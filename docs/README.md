# Documentation

How the mayadev documentation is organized and kept current. It follows the process RigModules uses (D21 in RigModules' `design/decisions.md`), so a change in either repo is documented the same way.

## Two kinds of documentation

| Where | Reader | Answers | Tense |
|---|---|---|---|
| `README.md`, `docs/`, `tests/README.md` | People using or changing mayadev: riggers, animators running the menu tools, tool writers | What does it do, and how do I use it? | What is true now |
| `py/scripts/docs/` (**deprecated**) | Anyone looking up one function | What is in this module? | Generated |

`py/scripts/docs/` is the old mkdocs site, now deprecated (see [The old mkdocs site](#the-old-mkdocs-site-deprecated)). Docstrings stay the function-level reference until something replaces its generated API pages.

**Design history lives in RigModules.** mayadev has no `design/` folder. The decisions that shaped it are in the RigModules repo: D24 (the boundary), D29 (the asset model), D30 (the Python package and the asset tools) D42 (the pose and animation library, FBX clips), D47 (the tool registry) and D49 (the user interfaces: layers, the registration pass, the prompter). When mayadev changes a behaviour one of those decided, the decision entry is updated in RigModules in the matching change.

## Pages and what each owns

Each topic has one owning page. Other pages link to it instead of repeating it. The README's summaries (the tool areas, the quick start) are the one allowed exception, and they stay consistent with the owning page.

| Page | Owns |
|---|---|
| [`../README.md`](../README.md) | What mayadev is, requirements, install, quick start, repo layout, links |
| [`setup.md`](setup.md) | Environment variables, `.mod` files, the startup sequence, the dev reload tools |
| [`architecture.md`](architecture.md) | The code: layers and dependency rules, the registration pass and its slots, how tools ask questions (the `Prompter`), the source map, the file handler pattern, and recipes for adding a tool, a file type, a handler or a slot |
| [`assets.md`](assets.md) | `bmaya.core.asset`: asset ids, `project.json`, `asset.json`, skeletons, rigs and looks (`rig.json`, `look.json`), the registry, publishes, local versions, source control, saving and loading by file type |
| [`clips.md`](clips.md) | The `exports` and `sources` bundles: FBX clips, the ControlAnim beside them, the bone map, the `animproperties` file format, the skeleton export |
| [`tools.md`](tools.md) | The tool registry and menu layout files, the two menus, every RigModules menu tool, the active rig, the two editors |
| [`rigmodules.md`](rigmodules.md) | Everything mayadev takes from RigModules: each command and `rigmodules` function, who calls it, and the rules for crossing the boundary |
| [`framework.md`](framework.md) | The general tooling: logger, progress manager, `Event`, events registry, batch framework, the Qt layer (base classes, the Qt prompter, forms), the doc generator |
| [`status.md`](status.md) | What each area of the code is worth keeping, and the known problems found reading it |
| [`../tests/README.md`](../tests/README.md) | Running the tests, what each folder covers, where a new test goes |

A topic that fits no page gets a new page here, a row in this table and a link in the README.

## When to update

A change updates its owning page **in the same change** when it touches anything a reader can see:

- An environment variable, a `.mod` file, the startup order or a dev tool → `setup.md`
- A module, class or folder, a layer rule, a slot, the `Prompter` protocol, a handler or a recipe step → `architecture.md`
- An asset id rule, a `project.json` or `asset.json` key, a file type, a registry query, a publish or version rule, a handler's arguments → `assets.md`
- A clip's folder, a file beside it, the `animproperties` format, the bone map or the skeleton export → `clips.md`
- A menu tool, a menu layout, a registry entry or an editor → `tools.md`
- A new RigModules command or `rigmodules` function that mayadev calls, or a rule about the boundary → `rigmodules.md`
- The logger, progress manager, `Event`, events registry, batch framework, Qt classes, the Qt prompter, form widgets or doc generator → `framework.md`
- Code deleted, adopted or found broken → `status.md`
- Test commands or layout → `tests/README.md`

**New things get docs, not just changed things.** A new tool, file type, handler or module is not done until its page has it. Search the pages for the old name after a rename, examples included. When a change touches nothing a reader can see (a refactor, a test-only change), say so in the change summary.

## Writing rules

- **Describe the code, not the plan.** Document what is built. Planned work goes in RigModules' `design/`, or under a clearly marked "Not built yet" note when a reader needs to know.
- **The code wins.** When a page and the code disagree, fix the page and say so in the change summary. When a page and RigModules' design documents disagree, flag it instead of picking one.
- **Use the code's names exactly**: function, file type key, JSON key, environment variable.
- **Command examples are Python `maya.cmds`, never MEL.** Flags are keyword arguments named by the long flag name, and a multi-use flag takes a list. Flag tables name the keyword without a leading `-`.
- **No import aliases.** Write `import bmaya.core.asset.handlers` and call `bmaya.core.asset.handlers.save(...)`. A `from bmaya.core.asset import Asset` is fine. The one alias is `import maya.cmds as cmds`.
- **Show, then list.** A short example first, then the full reference table.
- **Plain Markdown in the repo.** The pages are reviewed in the same diff as the code.

## The old mkdocs site (deprecated)

`py/scripts/docs/` with `py/scripts/mkdocs.yml` and the generator `batch/docgen` is deprecated. This folder is the maintained documentation.

- **Guides:** `guides/Mayadev Env Setup.md` and `guides/Asset Layout.md` are replaced by [`setup.md`](setup.md), [`tools.md`](tools.md), [`assets.md`](assets.md) and [`clips.md`](clips.md). Each carries a deprecation banner and is no longer edited. Fix this folder's pages, not those.
- **Generated API pages:** they have no replacement yet, so they stay as the per-function reference. They are not extended: no new pages by hand, and the generator is not changed except to keep it running. It logs a deprecation warning when it runs.
- **Index and config:** `docs/index.md` and `mkdocs.yml` say the site is deprecated and point here.
- **Removing it** (the site, `mkdocs.yml`, `batch/docgen` and the mkdocs install) is a later step, when the API pages are no longer wanted. Nothing in the code imports any of it.

## Tested examples

Not yet: no test reads an example out of the docs. The RigModules suite does this for its README (`tests/maya/concepts/test_docs_examples.py`). The candidates here are the asset examples in [`assets.md`](assets.md), which need only Python and a temporary projects root, and the `animproperties` example in [`clips.md`](clips.md). They are listed in [`status.md`](status.md) as proposed tests.
