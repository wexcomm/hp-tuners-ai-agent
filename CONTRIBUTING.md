# Contributing to HP Tuners AI Agent

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

- Be respectful and constructive
- Focus on what's best for the community and vehicle safety
- Show empathy towards other community members

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported
2. Open a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Vehicle platform and OBD-II adapter used
   - Python version and operating system

### Suggesting Features

1. Check if the feature has been suggested
2. Open a new issue with:
   - Clear use case
   - Vehicle platforms it would support
   - Potential implementation approach

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Update documentation
6. Commit with clear messages (`git commit -m 'Add amazing feature'`)
7. Push to your fork (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/wexcomm/hp-tuners-ai-agent.git
cd hp-tuners-ai-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install -e ".[dev]"
```

## Code Standards

### Python Style
- Follow PEP 8
- Use type hints where applicable
- Maximum line length: 100 characters
- Use meaningful variable names

### Documentation
- Docstrings for all public functions/classes
- Google-style docstrings preferred
- Update README.md if adding features
- Add examples for new vehicle platforms

### Testing
- Write tests for new features
- Ensure existing tests pass
- Test on actual vehicle hardware when possible
- Use pytest for testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

## Vehicle Platform Guidelines

When adding support for new vehicle platforms:

1. **Research First**
   - Understand the ECU architecture
   - Identify OBD-II PIDs and Mode 22 commands
   - Know the transmission type and limits
   - Document fuel system (DI vs port injection)

2. **Safety First**
   - Document known issues and limitations
   - Include maintenance checklists
   - Provide clear warnings about risks
   - Never bypass stock safety limits

3. **Required Files**
   - Vehicle profile JSON in `templates/`
   - Tuning guide in `docs/references/`
   - Controller class in `src/`

4. **Example Structure**
```python
class NewPlatformController:
    def __init__(self, ecu_controller):
        self.ecu = ecu_controller
        
    def get_specific_pids(self):
        # Return platform-specific PIDs
        pass
        
    def analyze_system_health(self, log_data):
        # Analyze platform-specific parameters
        pass
        
    def generate_tune(self, octane, mods):
        # Generate safe tune for platform
        pass
```

## Commit Message Guidelines

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit first line to 72 characters
- Reference issues and pull requests

Example:
```
Add LFX 3.6L V6 support

- Direct injection fuel system monitoring
- High compression knock analysis
- 6T70 transmission tuning

Closes #123
```

## Safety and Liability

**CRITICAL**: This software modifies vehicle ECUs. Contributors must:

1. **Never** suggest modifications that compromise safety
2. **Always** include appropriate warnings
3. **Document** all risks clearly
4. **Verify** changes on test vehicles before submitting
5. **Respect** manufacturer guidelines and emissions laws

## Questions?

- Open an issue for questions
- Join discussions in existing issues
- Contact maintainers if unsure

## Recognition

Contributors will be acknowledged in:
- README.md contributors section
- Release notes
- Project documentation

Thank you for contributing to safer, more informed ECU tuning!