## Summary

Brief description of the change and why it is needed.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update
- [ ] Refactor

## Testing

- [ ] `make test` passes
- [ ] `make all` passes
- [ ] `ruff check .` and `black --check .` pass
- [ ] `yamllint -c .yamllint .` passes
- [ ] `python tools/gen_protocol.py --check` and `python tools/gen_platform_caps.py --all --check` pass

## Checklist

- [ ] I have run `python tools/gen_platform_caps.py --all` and committed any generated changes
- [ ] I have run `python tools/gen_protocol.py` and committed any generated changes
- [ ] I have added or updated tests where appropriate
- [ ] I have updated the documentation if needed
- [ ] My commits are signed off (`git commit -s`)
- [ ] My changes generate no new compiler warnings
