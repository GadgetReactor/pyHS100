# pyHS100
Python Library to control TPLink Switch (HS100 / HS110)

# Usage
```python
from pyHS100 import SmartPlug

plug = SmartPlug("10.10.10.0")
print(plug.get_sysinfo())
print(plug.state)

plug.turn_on()
plug.turn_off()

plug.get_emeter_realtime()
```

For all available API functions run ```help(SmartPlug)```

# Example
There is also a simple tool for testing connectivity in examples, to use:
```python
python -m examples.cli <ip>
```
