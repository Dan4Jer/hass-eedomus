# Hass-Eedomus Coding Standards Skill

## Overview

This skill defines coding standards, commit conventions, and versioning practices for the hass-eedomus project.

## Quick Start

### 1. Check Code Formatting

```bash
# Navigate to project
cd ${LOCAL_REPO_PATH}

# Format with black
black custom_components/eedomus/

# Sort imports
isort custom_components/eedomus/

# Check linting
flake8 custom_components/eedomus/
```

### 2. Use Commit Template

```bash
# Copy template to your commit message
cp ~/.vibe/skills/hass-eedomus-coding-standards/templates/commit-template.txt /tmp/commit.msg

# Edit and use
nano /tmp/commit.msg
git commit -F /tmp/commit.msg
```

## Templates Included

| Template | Purpose | Usage |
|----------|---------|-------|
| `commit-template.txt` | Standardized commit messages | Copy to commit message file |
| `python-module-template.py` | Python module structure | Copy for new modules |
| `pyproject-toml-template.toml` | Project configuration | Reference for updates |
| `manifest-json-template.json` | Integration manifest | Reference for updates |

## Coding Standards Summary

### Formatting
- **Line Length**: 88 characters (black config)
- **Imports**: Grouped (future, stdlib, 3rd-party, HA, local)
- **Tools**: black, isort, flake8

### Type Hints
- **Required**: All functions, methods, class attributes
- **Optional**: Use `Optional[T]` or `T | None`
- **Collections**: Use `List[T]`, `Dict[K, V]`, etc.

### Docstrings
- **Format**: Google-style
- **Required**: All public classes and functions
- **Content**: Describe purpose, parameters, returns, exceptions

### Commit Messages
- **Format**: `type(scope): subject`
- **Types**: feat, fix, docs, style, refactor, perf, test, chore, revert
- **Scopes**: light, sensor, coordinator, options_flow, etc.
- **Subject**: Imperative, lowercase first letter, no period

### Versioning
- **Format**: Semantic Versioning (MAJOR.MINOR.PATCH)
- **Files**: pyproject.toml, manifest.json, README.md
- **Procedure**: Update all version files together, create git tag

## Validation

### Pre-commit Checklist

- [ ] Code formatted with black
- [ ] Imports sorted with isort
- [ ] No flake8 errors
- [ ] All functions have type hints
- [ ] All public code has docstrings
- [ ] Commit message follows template
- [ ] No sensitive data in code

### Code Review Checklist

- [ ] Branch follows naming conventions
- [ ] All commits have descriptive messages
- [ ] Tests pass
- [ ] Documentation updated (if needed)
- [ ] Version numbers updated (if releasing)

## Home Assistant 2026+ Compatibility

### API Changes to Note

| Old API | New API | Notes |
|---------|---------|-------|
| `async_track_state_change` | `async_track_state_change_event` | Event-based |
| `Store.async_save()` | `await store.async_save()` | Now async |
| `WSType` | N/A | Removed in 2026.02 |
| `register_built_in_panel` | `async_register_built_in_panel` | New async API |

### Compatibility Patterns

```python
# Version detection
from homeassistant.const import __version__ as HA_VERSION

def is_ha_2026_or_newer() -> bool:
    if HA_VERSION is None:
        return False
    major, minor, _ = HA_VERSION.split('.')[:3]
    return int(major) >= 2026

# Fallback pattern
if is_ha_2026_or_newer():
    # Use new API
    await async_register_built_in_panel(hass, ...)
else:
    # Use old API
    register_built_in_panel(hass, ...)
```

## Related Files

- **Skill File**: `SKILL.md` (detailed documentation)
- **Project**: [Dan4Jer/hass-eedomus](https://github.com/Dan4Jer/hass-eedomus)
- **Python Style**: PEP 8, Google style docstrings

## License

MIT License - See SKILL.md for details
