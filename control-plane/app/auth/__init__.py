"""身份与租户上下文（P2）。"""

from app.auth.dependencies import require_principal
from app.auth.oidc import OidcError, OidcMetadata, OidcProvider
from app.auth.principal import Principal

__all__ = ["OidcError", "OidcMetadata", "OidcProvider", "Principal", "require_principal"]
