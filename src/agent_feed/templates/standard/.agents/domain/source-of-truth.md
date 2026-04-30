# Source Of Truth

Define durable fact ownership for {{PROJECT_NAME}}.

## Ownership

1. Public API truth:
   - Owner document or module.
2. Durable state truth:
   - Owner document or module.
3. Event/audit truth:
   - Owner document or module.
4. Generated/projection truth:
   - Owner document or module.

## Recovery Principle

Recovery should reconstruct from stable facts and documented ownership rather than from incidental implementation state.
