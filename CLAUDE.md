# Project Instructions for Claude

This is your internship project workspace. Claude (via Claude Code) is your AI pair programmer.

## Workflow

1. **Start each session** by creating a session log: `log/session-YYYY-MM-DD.md`
2. **Commit frequently** using the `.gitmessage` template
3. **Update PROJECT.md** when stage or module progress changes
4. **Check off TODO items** as you complete them
5. **Log milestones** in UPDATE_LOG.md for significant achievements
6. **Update session-handoff.md** at the end of each session

## Commit Convention

Every commit must follow this format (`git commit` opens the template):

```
[YYYY-MM-DD] Type: short description

## Progress
- <what you accomplished>

## Problems
- [Tag] <blocker description> | None

## Insights
- [Tag] <discovery, tip, or pattern> | None

## Plan
- <next steps>
```

Types: Feat | Fix | Learn | Doc | Chore | Refactor | Test

## Project Files

| File | Purpose |
|------|---------|
| `PROJECT.md` | Project overview, stage, module progress |
| `TODO.md` | Task tracking with priorities and dependencies |
| `UPDATE_LOG.md` | Milestone log — record key achievements |
| `session-handoff.md` | Context handoff between sessions |
| `log/session-*.md` | Detailed session logs |
| `feedback/` | Mentor feedback (committed by mentor) |
| `meetings/` | 1:1 meeting notes |
| `docs/` | Project documentation |

## Tags

Use these tags in Problems and Insights sections:

Auth | API | Database | CORS | Middleware | Validation |
React | State | CSS | Routing | Form | Performance |
Build | Deploy | Docker | CI | Env |
Git | Testing | Debug | Architecture | Security
