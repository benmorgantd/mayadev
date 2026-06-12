# Reference Component: `bmaya.core.progressmanager`

## Module Level Context
No module documentation provided.

---
## Object Taxonomy Reference (Dynamic Introspection)

### ⚙️ Global Constants & Configurations

| Constant Name | Live Runtime Value | Type / Category |
| :--- | :--- | :--- |
| `Callable` | `typing.Callable` | Runtime Extracted Value |
| `Optional` | `typing.Optional` | Runtime Extracted Value |

---
### 🏷️ `CLASS` :: **ProgressManager**

**Description Summary:**
No class descriptions detailed.

#### Methods & Interceptors

#### 🛠️ `end(self) -> None`

```text
Clean up state and signal that progress is finished.
```


#### 🛠️ `increment(self, amount: int = 1, status: Optional[str] = None) -> None`

```text
Increment current progress by a specific amount.
```


#### 🛠️ `register_callback(self, callback: Callable[[], NoneType]) -> None`

```text
Hook for the UI to listen for updates.
```


#### 🛠️ `start(self, status: str, max_value: int = 100) -> None`

```text
Explicitly kick off a progress tracking session.
```


#### 🛠️ `update(self, value: int, status: Optional[str] = None) -> None`

```text
Update progress value and optionally the status text from anywhere.
```



---