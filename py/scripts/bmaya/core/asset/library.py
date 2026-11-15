"""The pose and animation library on disk: sources, listing, the index, search and masks (RigModules design/library-browser.md, D51).

Plain Python with no Maya import. The files are RigModules' ControlPose and ControlAnim (D34, D42), written and read by
bmaya.maya code. What this module knows is where they live, how to find them, and what to do with them as files: list,
rename, delete, search. What a file holds comes from a reader the caller passes to Index (RigModules'
getRigDataFileInfo, through bmaya.maya.librarybrowser), so this module runs in plain Python and in tests.

A source is a folder pair, controlposes and controlanims, with a label and a write rule:

    Approved   the asset's own folders, in source control. Read only here.
    Shared     the skeleton asset's folders, when the asset uses another asset's skeleton. Read only here.
    User       <projects root>\\user\\<login>\\animlibrary\\<asset id>\\controlposes and controlanims. Where saves go.

    sources = library.sources(asset)
    files = library.list_files(sources[-1], library.POSE)
    entries = library.Index(reader).entries(files, context=rig_root)
    shown = library.filter_entries(entries, library.parse_query("tag:fist hand"))
"""

from __future__ import annotations

import dataclasses
import getpass
import os
import re
import shutil
from collections.abc import Callable

from . import assetid, versions
from .asset import Asset
from .project import ProjectError, projects_root, read_json, write_json

POSE = "pose"
ANIMATION = "animation"
KINDS = (POSE, ANIMATION)

# The project.json file types whose folders hold each kind.
FOLDER_TYPE = {POSE: "controlposes", ANIMATION: "controlanims"}
SUFFIX = {POSE: ".controlpose.json", ANIMATION: ".controlanim.json"}
# Files written before the suffixes: <name>.json. They are listed, and renaming one gives it the new suffix.
LEGACY_SUFFIX = ".json"
COMPANION_SUFFIXES = (".png",)   # a thumbnail beside a file (phase 5) follows it through a rename and a delete

APPROVED = "approved"
SHARED = "shared"
USER = "user"
# The sources of a Mask. USER is the third.
RIG = "rig"
TEAM = "team"

USER_FOLDER = "animlibrary"
MASKS_FILE = "masks.json"
MASKS_FORMAT_VERSION = 1

# A file name becomes a name on disk and in the list: the rule of a clip name, in one place (RigModules D42).
NAME_RULE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_ -]*$")


class LibraryError(RuntimeError):
    """A library operation that can't be done: an unknown name, a name taken, a read-only source."""


# ---- sources and files --------------------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class LibrarySource:
    key: str                          # APPROVED, SHARED or USER
    label: str
    folders: dict[str, str]           # kind -> folder
    writable: bool                    # whether rename and delete work here


@dataclasses.dataclass(frozen=True)
class LibraryFile:
    path: str
    name: str
    kind: str
    source: str                       # the LibrarySource key
    writable: bool
    modified: float                   # the file's modified time
    legacy: bool                      # <name>.json, written before the suffixes


def login() -> str:
    """The OS user, the name of the user's own library folder."""
    return getpass.getuser()


def user_root(root: str | None = None) -> str:
    """The folder that holds the signed-in user's own files: <projects root>\\user\\<login>."""
    return os.path.join(os.path.normpath(root) if root else projects_root(), assetid.RESERVED_ROOT, login())


def user_source(asset: Asset) -> LibrarySource:
    """The user's own library of an asset. Pure: the folders needn't exist, and the asset needn't be on disk."""
    base = os.path.join(user_root(asset.root), USER_FOLDER, *assetid.tokens(asset.id))
    return LibrarySource(USER, "User", {kind: os.path.join(base, FOLDER_TYPE[kind]) for kind in KINDS}, True)


def sources(asset: Asset) -> list[LibrarySource]:
    """Approved, Shared (when the asset uses another asset's skeleton) and User, in that order. Approved and Shared
    are left out while their asset isn't on disk, so an asset that was never created still has its User library."""
    found = []
    if asset.exists():
        found.append(_asset_source(APPROVED, "Approved", asset))
        skeleton = asset.skeleton
        if not assetid.equals(skeleton, asset.id):
            owner = Asset(skeleton, asset.root)
            if owner.exists():
                found.append(_asset_source(SHARED, "Shared", owner))
    found.append(user_source(asset))
    return found


def _asset_source(key: str, label: str, asset: Asset) -> LibrarySource:
    return LibrarySource(key, label, {kind: asset.path(FOLDER_TYPE[kind]) for kind in KINDS}, False)


def file_path(folder: str, kind: str, name: str) -> str:
    """Where <name> is saved in a folder: <name>.controlpose.json or <name>.controlanim.json."""
    return os.path.join(folder, check_name(name) + SUFFIX[kind])


def find_file(folder: str, kind: str, name: str) -> str | None:
    """The file called name in a folder: the suffixed one, else a legacy <name>.json, else None."""
    for path in (os.path.join(folder, name + SUFFIX[kind]), os.path.join(folder, name + LEGACY_SUFFIX)):
        if os.path.isfile(path):
            return path
    return None


def check_name(name: str) -> str:
    if not isinstance(name, str) or not NAME_RULE.match(name):
        raise LibraryError(f"{name!r} is not a usable name. Use letters, digits, '_', '-' and spaces, starting with a letter or digit.")
    return name


def list_files(source: LibrarySource, kind: str) -> list[LibraryFile]:
    """The files of one kind in a source, sorted by name. A folder that doesn't exist holds none. When a name has both
    a suffixed and a legacy file, the suffixed one is listed."""
    folder = source.folders[kind]
    suffix = SUFFIX[kind]
    other_suffixes = tuple(SUFFIX[other] for other in KINDS if other != kind)
    found: dict[str, LibraryFile] = {}
    try:
        entries = list(os.scandir(folder))
    except OSError:
        return []
    for entry in entries:
        if not entry.is_file():
            continue
        if entry.name.endswith(suffix):
            name, legacy = entry.name[:-len(suffix)], False
        elif entry.name.endswith(LEGACY_SUFFIX) and not entry.name.endswith(other_suffixes):
            name, legacy = entry.name[:-len(LEGACY_SUFFIX)], True
        else:
            continue
        if not name or (name in found and legacy):
            continue
        found[name] = LibraryFile(entry.path, name, kind, source.key, source.writable, entry.stat().st_mtime, legacy)
    return sorted(found.values(), key=lambda item: item.name.casefold())


def free_name(source: LibrarySource, kind: str, prefix: str = "") -> str:
    """The first unused <prefix>_001, <prefix>_002, ... in a source. The prefix defaults to the kind."""
    prefix = prefix or kind
    taken = {item.name.casefold() for item in list_files(source, kind)}
    number = 1
    while f"{prefix}_{number:03d}".casefold() in taken:
        number += 1
    return f"{prefix}_{number:03d}"


def rename_file(item: LibraryFile, new_name: str) -> LibraryFile:
    """Renames a file in a writable source, with its companions (a thumbnail). A legacy file gets the new suffix.
    Raises LibraryError for a name that is taken or not usable."""
    _require_writable(item)
    folder = os.path.dirname(item.path)
    target = file_path(folder, item.kind, new_name)
    if new_name.casefold() != item.name.casefold() and find_file(folder, item.kind, new_name):
        raise LibraryError(f"There is already a {item.kind} called {new_name!r}.")
    os.replace(item.path, target)
    for old, new in zip(_companions(item), _companions(dataclasses.replace(item, path=target, name=new_name, legacy=False))):
        if os.path.isfile(old):
            os.replace(old, new)
    return dataclasses.replace(item, path=target, name=new_name, legacy=False, modified=os.path.getmtime(target))


def delete_file(item: LibraryFile, root: str) -> None:
    """Deletes a file in a writable source, with its companions. A local version copy is kept (root is the projects root)."""
    _require_writable(item)
    versions.version(item.path, root)
    for path in (item.path, *_companions(item)):
        if os.path.isfile(path):
            os.remove(path)


def _companions(item: LibraryFile) -> list[str]:
    stem = item.path[:-len(LEGACY_SUFFIX if item.legacy else SUFFIX[item.kind])]
    return [stem + suffix for suffix in COMPANION_SUFFIXES]


def _require_writable(item: LibraryFile) -> None:
    if not item.writable:
        raise LibraryError(f"{item.name!r} is in the {item.source} library, which can't be changed here. Copy it to your own library first.")


def copy_to_user(item: LibraryFile, user: LibrarySource) -> str:
    """Copies a file into the user's own library under its name, and returns the new path. Never overwrites."""
    folder = user.folders[item.kind]
    target = file_path(folder, item.kind, item.name)
    if find_file(folder, item.kind, item.name):
        raise LibraryError(f"Your library already has a {item.kind} called {item.name!r}.")
    os.makedirs(folder, exist_ok=True)
    shutil.copy2(item.path, target)
    return target


# ---- the index ----------------------------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class FileInfo:
    """What a file holds, as a Reader returns it. error is set, and the rest has its defaults, for a file that could
    not be read. The fields are those of RigModules' getRigDataFileInfo (rigmodules.library.DataFileInfo)."""

    error: str = ""
    kind: str = ""
    meta: dict = dataclasses.field(default_factory=dict)
    frame_rate: float = 0.0
    start_frame: float = 0.0
    end_frame: float = 0.0
    control_count: int = 0
    channel_count: int = 0
    unmatched_controls: tuple[tuple[str, str], ...] = ()


Reader = Callable[[list[str], str], list[FileInfo]]   # (paths, context) -> one FileInfo per path, in order


@dataclasses.dataclass(frozen=True)
class LibraryEntry:
    """A listed file and what it holds."""

    file: LibraryFile
    info: FileInfo

    @property
    def name(self) -> str:
        return self.file.name

    @property
    def path(self) -> str:
        return self.file.path

    @property
    def kind(self) -> str:
        return self.file.kind

    @property
    def source(self) -> str:
        return self.file.source

    @property
    def tags(self) -> list[str]:
        return _strings(self.info.meta.get("tags"))

    @property
    def regions(self) -> list[str]:
        return _strings(self.info.meta.get("rigRegions"))

    @property
    def description(self) -> str:
        return str(self.info.meta.get("description", ""))

    def meta(self, key: str) -> str:
        return str(self.info.meta.get(key, ""))


def _strings(value: object) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


class Index:
    """What each file holds, read once and cached by path, modified time and context. A listing reads only the files
    that are new or changed since the last one, in one call of the reader. context is whatever the reader's answer
    depends on besides the file: for RigModules, the rig root (which controls a file's controls match)."""

    def __init__(self, reader: Reader):
        self._reader = reader
        self._cache: dict[str, tuple[float, str, FileInfo]] = {}

    def entries(self, files: list[LibraryFile], context: str = "") -> list[LibraryEntry]:
        stale = [item for item in files if self._cache.get(item.path, (None, None, None))[:2] != (item.modified, context)]
        if stale:
            infos = self._reader([item.path for item in stale], context)
            if len(infos) != len(stale):
                raise LibraryError(f"The reader returned {len(infos)} results for {len(stale)} files.")
            for item, info in zip(stale, infos):
                self._cache[item.path] = (item.modified, context, info)
        return [LibraryEntry(item, self._cache[item.path][2]) for item in files]

    def forget(self, path: str) -> None:
        self._cache.pop(path, None)


# ---- search -------------------------------------------------------------------------------------------------

# Terms that match a field: `tag:fist`. The first group is a part of the value (case-insensitive), the second the
# whole value.
CONTAINS_FIELDS = ("tag", "template", "skeleton", "by", "category", "asset")
EQUALS_FIELDS = ("source", "kind", "status", "region")
FIELDS = CONTAINS_FIELDS + EQUALS_FIELDS

_TOKEN = re.compile(r'(?:\w+:)?"[^"]*"|\S+')


@dataclasses.dataclass(frozen=True)
class Query:
    words: tuple[str, ...] = ()
    terms: tuple[tuple[str, str], ...] = ()   # (field, value), the field lower case

    def term(self, field: str) -> list[str]:
        return [value for name, value in self.terms if name == field]


def parse_query(text: str) -> Query:
    """Splits the search box into free words and `field:value` terms. A value with spaces is quoted: tag:"hard hit".
    Anything with an unknown field is a free word, so a name that contains a colon still finds."""
    words, terms = [], []
    for token in _TOKEN.findall(text or ""):
        field, colon, value = token.partition(":")
        if colon and field.casefold() in FIELDS and value.strip('"'):
            terms.append((field.casefold(), value.strip('"')))
        elif token.strip('"'):
            words.append(token.strip('"'))
    return Query(tuple(words), tuple(terms))


def format_term(field: str, value: str) -> str:
    """The text of one term, quoted when the value has a space. What a facet chip puts in the search box."""
    return f'{field}:"{value}"' if " " in value else f"{field}:{value}"


def has_term(text: str, field: str, value: str) -> bool:
    """Whether the search text has the term field:value, the value compared ignoring case."""
    return any(name == field and wanted.casefold() == value.casefold() for name, wanted in parse_query(text).terms)


def toggle_term(text: str, field: str, value: str) -> str:
    """The search text with the term field:value added, or taken out when it is there already. What picking a facet
    does to the search box, so the box always shows what filters the list."""
    tokens = _TOKEN.findall(text or "")
    kept = [token for token in tokens if not has_term(token, field, value)]
    if len(kept) == len(tokens):
        kept.append(format_term(field, value))
    return " ".join(kept)


def matches(entry: LibraryEntry, query: Query) -> bool:
    """Every word is in the name, a tag or the description, and every term matches its field."""
    haystack = [entry.name, entry.description, *entry.tags]
    for word in query.words:
        if not any(word.casefold() in text.casefold() for text in haystack):
            return False
    return all(_term_matches(entry, field, value) for field, value in query.terms)


def _term_matches(entry: LibraryEntry, field: str, value: str) -> bool:
    wanted = value.casefold()
    values = {
        "tag": entry.tags,
        "template": [entry.meta("template")],
        "skeleton": [entry.meta("skeletonId")],
        "by": [entry.meta("author")],
        "category": [entry.meta("category")],
        "asset": [entry.meta("assetId")],
        "source": [entry.source],
        "kind": [entry.kind],
        "status": [entry.meta("status")],
        "region": entry.regions,
    }[field]
    if field in CONTAINS_FIELDS:
        return any(wanted in item.casefold() for item in values)
    return any(wanted == item.casefold() for item in values)


def filter_entries(entries: list[LibraryEntry], query: Query) -> list[LibraryEntry]:
    """The entries that match, sorted by name."""
    return sorted((entry for entry in entries if matches(entry, query)), key=lambda entry: entry.name.casefold())


# ---- masks --------------------------------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class MaskItem:
    """One filter on a rig's controls, by markup: each field given must match, a field left out matches anything. The
    fields are those of rigmodules.query.get_rig_controls: the module's type, a control's side and usage."""

    module_type: str | None = None
    side: str | None = None
    usage: str | None = None


@dataclasses.dataclass(frozen=True)
class Mask:
    """A named set of controls picked by markup, never by name, so it works on any rig of the template. A control is in
    the mask when any item matches it. source is RIG for the masks built from the active rig, TEAM and USER for saved ones."""

    name: str
    items: tuple[MaskItem, ...]
    source: str = USER

    def matches(self, module_type: str, side: str, usage: str) -> bool:
        return any(
            all(wanted is None or wanted == actual for wanted, actual in zip(
                (item.module_type, item.side, item.usage), (module_type, side, usage)))
            for item in self.items)


_ITEM_KEYS = {"moduleType": "module_type", "side": "side", "usage": "usage"}


def masks_path(source: LibrarySource) -> str:
    """The masks file of a source: beside its two folders, so a team's masks go with the asset and a user's with their own."""
    return os.path.join(os.path.dirname(source.folders[POSE]), MASKS_FILE)


def read_masks(path: str, source: str) -> list[Mask]:
    """The masks in a file, or none when it doesn't exist. Raises LibraryError for a file that isn't a masks file."""
    if not os.path.isfile(path):
        return []
    try:
        data = read_json(path)
    except ProjectError as error:
        raise LibraryError(str(error)) from None
    if data.get("formatVersion") != MASKS_FORMAT_VERSION or not isinstance(data.get("masks"), list):
        raise LibraryError(f"{path}: not a masks file of version {MASKS_FORMAT_VERSION}.")
    masks = []
    for entry in data["masks"]:
        name, raw_items = entry.get("name") if isinstance(entry, dict) else None, entry.get("items") if isinstance(entry, dict) else None
        if not isinstance(name, str) or not name or not isinstance(raw_items, list):
            raise LibraryError(f"{path}: every mask needs a name and a list of items.")
        items = []
        for raw in raw_items:
            if not isinstance(raw, dict) or set(raw) - set(_ITEM_KEYS) or not all(isinstance(v, str) for v in raw.values()):
                raise LibraryError(f"{path}: mask {name!r} has an item that is not made of {sorted(_ITEM_KEYS)} strings.")
            items.append(MaskItem(**{_ITEM_KEYS[key]: value for key, value in raw.items()}))
        masks.append(Mask(name, tuple(items), source))
    return masks


def write_masks(path: str, masks: list[Mask]) -> None:
    """Writes a masks file, one mask per name, in the order given."""
    names = [mask.name.casefold() for mask in masks]
    if len(set(names)) != len(names):
        raise LibraryError("Mask names must be different.")
    reverse = {value: key for key, value in _ITEM_KEYS.items()}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    write_json(path, {
        "formatVersion": MASKS_FORMAT_VERSION,
        "masks": [{"name": mask.name, "items": [
            {reverse[field]: value for field, value in dataclasses.asdict(item).items() if value is not None}
            for item in mask.items]} for mask in masks],
    })


def saved_masks(asset: Asset) -> list[Mask]:
    """The masks saved for an asset: the team's (beside the Approved folders) then the user's, with a user mask
    replacing a team mask of the same name."""
    found: dict[str, Mask] = {}
    for source in sources(asset):
        if source.key in (APPROVED, USER):
            for mask in read_masks(masks_path(source), TEAM if source.key == APPROVED else USER):
                found[mask.name.casefold()] = mask
    return sorted(found.values(), key=lambda mask: mask.name.casefold())


def save_mask(asset: Asset, mask: Mask) -> str:
    """Saves a mask in the user's own masks file, replacing one of the same name. Returns the file."""
    path = masks_path(user_source(asset))
    kept = [existing for existing in read_masks(path, USER) if existing.name.casefold() != mask.name.casefold()]
    write_masks(path, [*kept, dataclasses.replace(mask, source=USER)])
    return path


def delete_mask(asset: Asset, name: str) -> None:
    """Removes a mask from the user's own masks file. A team mask can't be removed here."""
    path = masks_path(user_source(asset))
    masks = read_masks(path, USER)
    kept = [mask for mask in masks if mask.name.casefold() != name.casefold()]
    if len(kept) == len(masks):
        raise LibraryError(f"You have no saved mask called {name!r}.")
    write_masks(path, kept)

