package main

import (
	"testing"
)

func TestFetchTerraformReleases(t *testing.T) {
	versions, err := fetchTerraformReleases()
	if err != nil {
		t.Fatalf("fetchTerraformReleases() returned error: %v", err)
	}

	if len(versions) == 0 {
		t.Error("fetchTerraformReleases() returned empty versions list")
	}

	// Check if we got some versions
	t.Logf("Found %d Terraform versions", len(versions))

	// Print all versions
	for _, version := range versions {
		t.Logf("%s", version)
	}

	// Basic validation: check that versions don't contain unexpected characters
	for _, version := range versions {
		if version == "" {
			t.Error("Found empty version string in results")
		}
		// Versions should typically start with a number
		if len(version) > 0 && (version[0] < '0' || version[0] > '9') {
			t.Logf("Warning: Version '%s' doesn't start with a number", version)
		}
	}
}
