# Draft variants for the X-fill interpretation

Both variants include Pavel's corrections (2026-10-19):

- rectangular pockets are 12x15 mm, 30 mm deep, centered in Y like the other
  pockets (12 mm across the block, 15 mm along it) - the earlier full-width
  channel reading (A2/B2) was REJECTED, those previews are kept only for history;
- legs: only the 4 corner ones (the 2 mid-length legs are gone).

Both variants are verified single-body solids (`body_count == 1`, now also a
mandatory test) and all 19 tests pass.

- variant A (`web_floor`, deep pockets only): the pocket floor IS an X-shaped
  web under the four DEEP pockets (30 mm deep, 5 mm floor left); the two
  shallow end pockets (15 mm) keep a solid floor. Open quarters go through
  the 5 mm floor to the bottom face.
- variant B (`cradle`): every pocket has a solid floor at its depth, with an
  X-shaped ridge (4 mm wide, 3 mm tall) rising from the floor inside the
  pocket - a semi-open cradle.

Each variant has top / iso / bottom previews. The bottom view shows the 4
corner legs fused to the block (the regression the first attempt failed).

Pick A or B (or describe corrections); then the model, tests and
verification report get finalized against the chosen variant.
