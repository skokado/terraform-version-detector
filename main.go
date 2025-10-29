package main

import (
	"fmt"
	"log"
	"net/http"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"path/filepath"

	"github.com/PuerkitoBio/goquery"
	"github.com/hashicorp/hcl/v2/hclparse"
	"github.com/hashicorp/hcl/v2/hclsyntax"
	"github.com/zclconf/go-cty/cty"
)

type TerraformConfig struct {
	RequiredVersion string
}

func extractStringFromExpr(expr hclsyntax.Expression) (string, error) {
	if tmpl, ok := expr.(*hclsyntax.TemplateExpr); ok {
		if len(tmpl.Parts) == 1 {
			if lit, ok := tmpl.Parts[0].(*hclsyntax.LiteralValueExpr); ok {
				if lit.Val.Type() == cty.String {
					return lit.Val.AsString(), nil
				}
			}
		}
	}

	if lit, ok := expr.(*hclsyntax.LiteralValueExpr); ok {
		if lit.Val.Type() == cty.String {
			return lit.Val.AsString(), nil
		}
	}

	return "", fmt.Errorf("unable to extract string from expression type %T", expr)
}

func parseTerraformFile(filename string) (*TerraformConfig, error) {
	parser := hclparse.NewParser()

	file, diags := parser.ParseHCLFile(filename)
	if diags.HasErrors() {
		return nil, fmt.Errorf("failed to parse HCL file: %s", diags)
	}

	body, ok := file.Body.(*hclsyntax.Body)
	if !ok {
		return nil, fmt.Errorf("unexpected body type")
	}

	for _, block := range body.Blocks {
		if block.Type == "terraform" && len(block.Labels) == 0 {
			if attr, exists := block.Body.Attributes["required_version"]; exists {
				version, err := extractStringFromExpr(attr.Expr)
				if err == nil {
					return &TerraformConfig{
						RequiredVersion: version,
					}, nil
				}
			}
		}
	}

	return &TerraformConfig{}, nil
}

func fetchTerraformReleases() ([][3]int, error) {
	// Fetch Terraform releases from https://releases.hashicorp.com/terraform/
	resp, err := http.Get("https://releases.hashicorp.com/terraform/")
	if err != nil {
		return nil, fmt.Errorf("failed to fetch releases: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	doc, err := goquery.NewDocumentFromReader(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to parse HTML: %w", err)
	}

	var versions [][3]int
	semverRegex := regexp.MustCompile(`^\d+\.\d+\.\d+$`)

	doc.Find("a").Each(func(i int, s *goquery.Selection) {
		href, exists := s.Attr("href")
		if exists && strings.HasPrefix(href, "/terraform/") {
			version := strings.TrimPrefix(href, "/terraform/")
			version = strings.TrimSuffix(version, "/")
			if version != "" && version != "index.json" {
				if semverRegex.MatchString(version) {
					parts := strings.Split(version, ".")
					major, _ := strconv.Atoi(parts[0])
					minor, _ := strconv.Atoi(parts[1])
					patch, _ := strconv.Atoi(parts[2])
					versions = append(versions, [3]int{major, minor, patch})
				}
			}
		}
	})

	// Sort versions in descending order using semver
	sort.Slice(versions, func(i, j int) bool {
		for k := 0; k < 3; k++ {
			if versions[i][k] != versions[j][k] {
				return versions[i][k] > versions[j][k]
			}
		}
		return false
	})

	return versions, nil
}

func main() {
	matches, err := filepath.Glob("*.tf")
	if err != nil {
		log.Fatal(err)
		return
	}
	var config *TerraformConfig
	for _, filename := range matches {
		parsedConfig, err := parseTerraformFile(filename)
		if err != nil {
			continue
		}
		if parsedConfig.RequiredVersion != "" {
			fmt.Printf("Found required_version specification in %s\n", filename)
			config = parsedConfig
			break
		}
	}

	if config == nil || config.RequiredVersion == "" {
		fmt.Println("No required_version specification found.")
		return
	}

	for _, versionConstraint := range strings.Split(config.RequiredVersion, ",") {
		versionConstraint = strings.TrimSpace(versionConstraint)
		fmt.Println(versionConstraint)
	}
}
