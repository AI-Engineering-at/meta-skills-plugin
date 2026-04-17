# Cleanup Log — meta-skills

> Every file removal that is NOT captured in a `git rm`/`git mv` commit is
> logged here with evidence. Covers: untracked files, build artefacts,
> 0-byte Windows/shell redirect leftovers, orphaned temp files.
>
> Purpose: traceability. Rule S1 (Joe confirms before delete) + Rule G1
> (cleanup documented after every change). Git alone cannot record the
> deletion of an untracked file, so this log fills the gap.

---

## 2026-04-16 — `nul` (0-byte Windows redirect leftover)

**What:** 0-byte file at meta-skills repo root named `nul`.

**Why it existed:** `hooks/run-hook.cmd:4` uses `2>nul` to swallow stderr.
On native Windows CMD `NUL` is the null-device and the redirect disappears.
When the same script is executed from a bash-on-Windows shell (Git Bash /
WSL), `nul` is interpreted as a literal filename and gets created as a
0-byte file in the cwd. The file then sat in the repo root untracked.

**What I did:** confirmed with Joe (S1), then:
```bash
rm ./nul
```

**Evidence — before:**
```
$ ls -la meta-skills/nul
-rw-r--r-- 1 Legion 197121 0 Apr 14 12:03 meta-skills/nul
```

**Evidence — after:**
```
$ ls meta-skills/nul
ls: cannot access 'meta-skills/nul': No such file or directory
exit=2
```

**Git trace:** None — file was untracked. That is exactly why this log
entry exists.

**Prevention follow-up (not done yet):** audit `hooks/run-hook.cmd` to
either (a) switch redirect to uppercase `NUL` (still Windows-only, bash
would still leak) or (b) wrap in `cmd /c "...2>nul"` explicitly so bash
can never misinterpret. Tracked as a potential tiny follow-up, not
blocking.
