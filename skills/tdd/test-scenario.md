Input: "I need to add a user authentication feature to the Flask app."
Expected: Agent should write tests FIRST before implementation code.
Pass: test|assert|def test_|pytest|expect|should.*fail|red.*green|write.*test.*first
Fail: ^let me implement|^here's the code|^first.*implement|def login|def authenticate
