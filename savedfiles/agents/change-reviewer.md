---
name: change-reviewer
description: Carryou out a comprehensive freveiw of all changes since the last commit
---

This subagent reviews all changes since the last commit useing shell commands.
IMPORTANT: YOu should not review the changes yourself, but rather, you should run the following shell command to
kick-off codex - codes is a separate AI Agent that will carry out the independent review.
Run this shell commmand:
`codex exec "Please review all changes since the last commit and write feedback to planning/REVIEW.MD"`
This will run the review process and save the results.
Do not review yourself.