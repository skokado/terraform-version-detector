# Terraform Version Detector in GitHub Actions

Automatic detection `required_version` in terraform block for [hashicorp/setup-terraform](https://github.com/hashicorp/setup-terraform) action step.

Basic usage:

```yaml
steps:
- uses: actions/checkout@v5

- uses: skokado/terraform-version-detector@v1
  id: terraform-version
  with:
    path: path/to/dir

- uses: hashicorp/setup-terraform@v3
  with:
    terraform_version: ${{ steps.terraform-version.outputs.terraform-version }}
```

## Examples

```yaml
steps:
- uses: actions/checkout@v5

# --- app1/terraform.tf
# terraform {
#   required_version = ">= 1.10.0, < 1.11.0"
# }
- uses: skokado/terraform-version-detector@v1.2
  id: sample1
  with:
    path: app1/

- run: echo ${{ steps.sample1.outputs.terraform-version }}
# => Latest of 1.10.x 
```

For more details, see Terraform documentation on [Version Constraints](https://developer.hashicorp.com/terraform/language/versions#version-constraints).

# Inputs

| Input | Description | Default |
|-------|-------------|---------|
| `path`  | Path to the directory containing Terraform configuration files. | `.` |

# Outputs

| Output | Description |
|--------|-------------|
| `terraform-version` | The detected Terraform version based on the `required_version` constraint.<br>If no version specified, use latest  release version. |
