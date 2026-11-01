SKILL_NAME := tracking-pension-deductions
SKILL_DIR := dist/$(SKILL_NAME)
SKILL_ZIP := $(abspath dist/$(SKILL_NAME)-skill.zip)

.PHONY: package-skill

package-skill:
	mkdir -p $(SKILL_DIR)/scripts $(SKILL_DIR)/references $(SKILL_DIR)/dist
	cp SKILL.md $(SKILL_DIR)/
	cp scripts/*.py $(SKILL_DIR)/scripts/
	cp references/*.md $(SKILL_DIR)/references/
	cp dist/template.html $(SKILL_DIR)/dist/
	rm -f $(SKILL_ZIP)
	cd dist && zip -q -r $(notdir $(SKILL_ZIP)) $(SKILL_NAME)
	rm -rf $(SKILL_DIR)