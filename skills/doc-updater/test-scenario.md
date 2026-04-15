Input: "I just deployed v2.12.0 of the voice gateway. Update all docs."
Expected: Agent should scan docs for stale version references, not manually edit one file.
Pass: scan|stale|version|parallel|scanner|update.*all|drift|consistency|doc-scanner
Fail: ^I'll update the README|^let me change the version in
