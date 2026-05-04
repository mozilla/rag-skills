# Local Development

Test skill changes locally before pushing to main.

## Setup

```bash
./scripts/dev-setup.sh
```

This creates a symlink from `~/.claude/skills/mozilla-semantic-skills` to your local repo. Changes to skill files are reflected immediately — no restart needed.

## Workflow

1. Edit `skills/<skill-name>/SKILL.md` or any supporting files
2. Start a Claude Code session: `claude`
3. Invoke the skill and test your changes
4. Commit and push when satisfied

## Teardown

```bash
./scripts/dev-setup.sh --clean
```

## Adding a new skill

1. Create `skills/<skill-name>/SKILL.md` with frontmatter:
   ```yaml
   ---
   name: <skill-name>
   description: <one-line trigger description>
   ---
   ```
2. Add `"./skills/<skill-name>"` to `.claude-plugin/marketplace.json`
3. Run dev-setup, test locally, then commit
