# api.inference.models declares foreign keys to scans.id and users.id.
# SQLAlchemy can only resolve those at Base.metadata.create_all()/Alembic
# autogenerate time if api.scans.models / api.user.models have themselves
# been imported somewhere first (see api/alembic/env.py, which does the same
# for exactly this reason). Importing them here — once, as a side effect of
# importing this package at all — means api.inference.models never depends
# on some *other* module having been imported first for its own foreign keys
# to resolve.
from api.scans import models as _scans_models  # noqa: F401
from api.user import models as _user_models  # noqa: F401
