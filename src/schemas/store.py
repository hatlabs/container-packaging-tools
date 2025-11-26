"""Pydantic models for validating container store definitions."""

from pydantic import BaseModel, Field, field_validator


class CategoryMetadata(BaseModel):
    """Category metadata for custom section organization."""

    id: str = Field(
        pattern=r"^[a-z][a-z0-9_-]*$",
        description="Category ID (lowercase with hyphens/underscores)",
    )
    label: str = Field(min_length=1, description="Human-readable category label")
    icon: str = Field(min_length=1, description="Icon identifier for the category")
    description: str | None = Field(
        None, description="Optional description of the category"
    )


class StoreFilter(BaseModel):
    """Filter criteria for a container store.

    Origin filtering is mandatory for performance optimization since container
    packages always come from custom repositories, never from upstream Debian
    or Raspberry Pi repositories. This enables efficient pre-filtering before
    applying more expensive tag/section filters.

    Filter Logic:
    - OR within each filter type (e.g., any of the specified origins)
    - AND between filter types (must match criteria from each specified type)
    """

    include_origins: list[str] = Field(
        min_length=1,
        description="Required: Repository origins (from APT Release 'Origin:' field). "
        "Must be non-empty for performance optimization.",
    )
    include_sections: list[str] = Field(
        default_factory=list,
        description="Optional: Debian sections to include",
    )
    include_tags: list[str] = Field(
        default_factory=list,
        description="Optional: Debian tags (debtags) to include",
    )
    include_packages: list[str] = Field(
        default_factory=list,
        description="Optional: Explicit package names to include",
    )


class StoreConfig(BaseModel):
    """Container store configuration.

    Defines how packages are filtered and displayed in cockpit-apt's store view.
    Each store represents a curated collection of container applications from
    specific repository origins.
    """

    # Store identity
    id: str = Field(
        pattern=r"^[a-z][a-z0-9-]*$",
        description="Store ID (lowercase with hyphens)",
    )
    name: str = Field(min_length=1, description="Human-readable store name")
    description: str = Field(min_length=1, description="Store description")

    # Assets (paths are validated at runtime)
    icon: str | None = Field(
        None,
        description="Path to store icon (24x24 or SVG)",
    )
    banner: str | None = Field(
        None,
        description="Path to store banner (recommended 1200x300 PNG)",
    )

    # Filter configuration (origin is mandatory)
    filters: StoreFilter = Field(description="Package filter criteria")

    # Optional custom categorization
    category_metadata: list[CategoryMetadata] = Field(
        default_factory=list,
        description="Optional custom category definitions for package organization",
    )

    @field_validator("id")
    @classmethod
    def validate_store_id(cls, v: str) -> str:
        """Validate store ID format."""
        if len(v) < 2:
            raise ValueError("Store ID must be at least 2 characters")
        return v
