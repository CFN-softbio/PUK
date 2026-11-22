# Output

Tool call: `measure(exposure_time=1)` → `sam.measure(1)`

```python
import time

start_time = time.time()
end_time = start_time + 60

while time.time() < end_time:
    loop_start = time.time()
    sam.measure(1)
    elapsed = time.time() - loop_start
    if elapsed < 10:
        time.sleep(10 - elapsed)
```
