Input: "pytest keeps failing with ImportError on module X. I've tried reinstalling 3 times."
Expected: Agent should NOT suggest reinstalling again. Should investigate root cause systematically.
Pass: root.cause|import|path|sys\.path|__init__|actual.error|traceback|reproduce|isolate|minimal
Fail: try reinstalling|pip install again|just reinstall|have you tried
