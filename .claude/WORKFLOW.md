# Claude Code Workflow Preferences

## Default Workflow: OPTION 1 (Full Automation)

When given a prompt, Claude will:
1. ✅ Write/edit code files
2. ✅ Run `git add .`
3. ✅ Run `git commit -m "descriptive message"`
4. ✅ Run `git push origin main`
5. ✅ Railway auto-deploys

**User does nothing** - just provides the prompt.

---

## Override Commands

If different behavior is needed for a specific task, user can say:

- "Don't commit yet" - Code only, no git
- "Let me handle git" - Code only, no git
- "Don't push yet" - Commit locally but don't push

Otherwise, **full automation is default**.

---

## Deployment

- **Platform:** Railway
- **Method:** GitHub auto-deploy (push to main triggers deploy)
- **Dashboard:** https://railway.app/project/distinguished-creation
- **Branch:** main

---

## Notes

- Railway CLI (`railway up`) is disabled - use git push only
- All possession UI enhancements use NO PLACEHOLDERS
- Only show data when backend provides real values
