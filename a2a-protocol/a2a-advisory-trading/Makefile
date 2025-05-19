##################################################
### Global variables for naming convention
##################################################

APP_NAME ?=adt
ENV_NAME ?=dev
AWS_REGION =us-east-1

##################################################
#### DO NOT CHANGE
##################################################

IAC_DIR :=iac
LAYER_DIR=iac/layers
LAYER_ZIP=a2a_core.zip
LAYER_KEY=layers/a2a_core.zip
RANDOM_NUM := $(shell date +%s | md5sum | head -c 16)
LAYER_BUCKET_NAME = $(APP_NAME)-$(ENV_NAME)-a2a-core-$(RANDOM_NUM)

##################################################
# Export variables for Terraform
export TF_VAR_app_name=$(APP_NAME)
export TF_VAR_env_name=$(ENV_NAME)
export TF_VAR_aws_region=$(AWS_REGION)

# Agent-specific deployment targets
AGENTS := market_analysis risk_assessment portfolio_manager trade_execution

# Configuration verification target
config:
	@echo "Current configuration:"
	@echo "APP_NAME: $$TF_VAR_app_name"
	@echo "ENV_NAME: $$TF_VAR_env_name"
	@echo "AWS_REGION: $$TF_VAR_aws_region"

##################################################
#### Deploy core
##################################################

IAC_DIR :=iac
LAYER_DIR=iac/layers
LAYER_ZIP=a2a_core.zip
LAYER_KEY=layers/a2a_core.zip
RANDOM_NUM := $(shell date +%s | md5sum | head -c 16)
LAYER_BUCKET_NAME = $(APP_NAME)-$(ENV_NAME)-a2a-core-$(RANDOM_NUM)

create-bucket:
	@echo "Creating S3 bucket if it doesn't exist..."
	@if aws s3 ls "s3://$(LAYER_BUCKET_NAME)" 2>&1 | grep -q 'NoSuchBucket'; then \
		if aws s3 mb s3://$(LAYER_BUCKET_NAME) --region $(AWS_REGION); then \
			echo "S3 bucket created successfully."; \
		else \
			echo "Failed to create S3 bucket"; \
			exit 1; \
		fi \
	else \
		echo "Bucket already exists, skipping creation."; \
	fi

zip-layer:
	@echo "Creating layer zip file..."
	@mkdir -p $(LAYER_DIR)
	@mkdir -p $(IAC_DIR)/temp/python
	@cp -r $(IAC_DIR)/a2a_core $(IAC_DIR)/temp/python/
	@echo "Installing dependencies..."
	@cd $(IAC_DIR)/temp && \
	pip install -r python/a2a_core/requirements.txt --target python && \
	zip -r ../layers/a2a_core.zip python && \
	if [ $$? -eq 0 ]; then \
		echo "Layer zip file created successfully in iac/layers/"; \
		rm -rf $(IAC_DIR)/temp; \
	else \
		echo "Failed to create layer zip file"; \
		rm -rf $(IAC_DIR)/temp; \
		exit 1; \
	fi


upload-layer: create-bucket zip-layer
	@echo "Uploading layer to S3..."
	@if aws s3 cp $(LAYER_DIR)/$(LAYER_ZIP) s3://$(LAYER_BUCKET_NAME); then \
		echo "Layer uploaded to S3 successfully."; \
	else \
		echo "Failed to upload layer to S3"; \
		exit 1; \
	fi

deploy-core: zip-layer upload-layer
	@echo "Core layer deployment completed successfully."

destroy-core:
	@echo "Removing layer from S3..."
	@if aws s3 rm s3://$(BUCKET_NAME)/$(LAYER_KEY); then \
		echo "Layer removed from S3 successfully."; \
	fi
	@echo "Removing S3 bucket..."
	@if aws s3 rb s3://$(BUCKET_NAME) --force; then \
		echo "S3 bucket removed successfully."; \
	fi
	@$(MAKE) clean

##################################################
#### Deploy shared
##################################################

deploy-shared: config
	cd $(IAC_DIR)/shared && \
	terraform init && \
	terraform apply -auto-approve

destroy-shared: config
	cd $(IAC_DIR)/shared && \
	terraform destroy -auto-approve

##################################################
#### Deploy agents
##################################################

deploy-market-analysis: config
	cd $(IAC_DIR)/agents/market_analysis && \
	terraform init && \
	terraform apply -auto-approve

destroy-market-analysis: config
	cd $(IAC_DIR)/agents/market_analysis && \
	terraform destroy -auto-approve

deploy-risk-assessment: config
	cd $(IAC_DIR)/agents/risk_assessment && \
	terraform init && \
	terraform apply -auto-approve

destroy-risk-assessment: config
	cd $(IAC_DIR)/agents/risk_assessment && \
	terraform destroy -auto-approve

deploy-portfolio-manager: config
	cd $(IAC_DIR)/agents/portfolio_manager && \
	terraform init && \
	terraform apply -auto-approve

destroy-portfolio-manager: config
	cd $(IAC_DIR)/agents/portfolio_manager && \
	terraform destroy -auto-approve

deploy-trade-execution: config
	cd $(IAC_DIR)/agents/trade_execution && \
	terraform init && \
	terraform apply -auto-approve

destroy-trade-execution: config
	cd $(IAC_DIR)/agents/trade_execution && \
	terraform destroy -auto-approve

.PHONY: config deploy-core deploy-shared deploy-market-analysis deploy-risk-assessment deploy-trade-execution deploy-portfolio-manager
