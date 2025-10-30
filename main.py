import argparse
import json
import sys
from enum import StrEnum
from pathlib import Path
from urllib.request import urlopen

import hcl2


class VersionOperator(StrEnum):
    # ref. https://developer.hashicorp.com/terraform/language/expressions/version-constraints#operators
    EQ = "="
    NE = "!="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    RIGHT_MOST = "~>"


def parse_right_most(version_spec: str) -> str:
    """Parse the right-most version specification into a pair of operators
    ref. right-most operator: https://developer.hashicorp.com/terraform/language/expressions/version-constraints#operators

    >>> parse_right_most("~> 1.2")
    '>= 1.2.0, < 2.0.0'

    >>> parse_right_most("~> 1.2.3")
    '>= 1.2.3, < 1.3.0'
    """
    if not version_spec.startswith(VersionOperator.RIGHT_MOST):
        raise ValueError("Not a right-most version specification")

    _, version = version_spec.split()
    parts = version.split(".")
    major = int(parts[0])
    minor = int(parts[1]) if len(parts) > 1 else 0
    patch = int(parts[2]) if len(parts) > 2 else 0

    lower_bound = f">= {major}.{minor}.{patch}"
    if len(parts) == 1:
        upper_bound = f"< {major + 1}.0.0"
    elif len(parts) == 2:
        upper_bound = f"< {major + 1}.0.0"
    else:
        upper_bound = f"< {major}.{minor + 1}.0"

    return f"{lower_bound}, {upper_bound}"


def check_version(version_spec: str, target_version: tuple[int, int, int]) -> bool:
    """Check if the target_version matches the version_spec.

    >>> check_version("!= 1.2.3", (1, 2, 3))
    False
    >>> check_version("= 1.2.3", (1, 2, 3))
    True
    >>> check_version(">= 1.2", (1, 2, 0))
    True
    >>> check_version("<= 1.2", (1, 2, 0))
    True
    >>> check_version("< 1.3", (1, 3, 0))
    False
    >>> check_version(">= 1.2, <= 1.3", (1, 2, 5))
    True
    >>> check_version("~> 1.2", (1, 2, 5))
    True
    >>> check_version("~> 1.2.0", (1, 3, 0))
    False
    """
    if version_spec.startswith(VersionOperator.RIGHT_MOST):
        version_spec = parse_right_most(version_spec)

    constraints = [spec.strip() for spec in version_spec.split(",")]
    for constraint in constraints:
        operator, version = constraint.split()
        version_parts = version.split(".")
        major = int(version_parts[0])
        minor = int(version_parts[1]) if len(version_parts) > 1 else 0
        patch = int(version_parts[2]) if len(version_parts) > 2 else 0
        parts = (major, minor, patch)

        if operator == VersionOperator.EQ and not target_version == parts:
            return False
        elif operator == VersionOperator.NE and not target_version != parts:
            return False
        elif operator == VersionOperator.GT and not target_version > parts:
            return False
        elif operator == VersionOperator.GTE and not target_version >= parts:
            return False
        elif operator == VersionOperator.LT and not target_version < parts:
            return False
        elif operator == VersionOperator.LTE and not target_version <= parts:
            return False

    return True


def fetch_terraform_releases() -> list[tuple[int, int, int]]:
    """Fetch Terraform releases from https://releases.hashicorp.com/terraform/index.json
    Returns a list of version tuples sorted by major, minor, patch in descending order.
    """
    url = "https://releases.hashicorp.com/terraform/index.json"
    with urlopen(url) as response:
        data = response.read().decode()

    data = json.loads(data)
    versions = list(data.get("versions", {}).keys())

    versions = [
        tuple(int(part) for part in version.split("."))
        for version in versions
        if all(part.isdigit() for part in version.split("."))
    ]

    # sort by major, minor, patch in desc.
    versions.sort(key=lambda v: (v[0], v[1], v[2]), reverse=True)
    return versions  # pyright: ignore[reportReturnType]


def main():
    parser = argparse.ArgumentParser(
        description="Detect Terraform required_version from .tf files"
    )
    parser.add_argument(
        "--path",
        type=str,
        help="Relative path to the Terraform configuration directory",
        required=False,
        default=".",
    )
    args = parser.parse_args()
    path = Path(args.path)

    if not path.exists():
        raise ValueError(f"The specified path does not exist: {path}")
    if path.is_file():
        raise ValueError(f"The specified path is a file, expected a directory: {path}")

    terraform_releases = fetch_terraform_releases()
    latest_release = terraform_releases[0]

    required_version: str | None = None
    found = False
    for tf_file in path.glob("*.tf"):
        if found:
            break

        with open(tf_file, "r") as file:
            parsed = hcl2.load(file)  # pyright: ignore[reportPrivateImportUsage]

        for terraform_block in parsed.get("terraform", []):
            if required_version := terraform_block.get("required_version"):
                print(f"Found version specification in {tf_file.name}", file=sys.stderr)
                found = True

    if not found:
        print("No version specification found, using latest.", file=sys.stderr)
        version_str = ".".join(list(map(str, latest_release)))
        print(version_str, end="")
        return

    assert required_version
    for version in terraform_releases:
        if check_version(required_version, version):
            version_str = ".".join(list(map(str, version)))
            print(version_str, end="")
            return


if __name__ == "__main__":
    main()
