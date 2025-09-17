# This scripts creates a lambda layer for strands agents & requests packages.
# It's compatible with arm64 CPU architecture and Python 3.13 version

#replace below parameters as per your environment

bucket_name="d2-lambda-layers"
layer_package_file="strands-agents-layer.zip"
layer_name="strands-agents-layer"
layer_description="strands-agents-sdk-and-requests-package"


# remove existing layer file, if it exists
rm $layer_package_file

#create a new temporary folder to install the packages
mkdir ./python
pip3 install -U requests -t ./python/ --python-version 3.13 --platform manylinux2014_aarch64 --only-binary=:all:
pip3 install -U strands-agents -t ./python/ --python-version 3.13 --platform manylinux2014_aarch64 --only-binary=:all:
pip3 install -U strands-agents-tools -t ./python/ --python-version 3.13 --platform manylinux2014_aarch64 --only-binary=:all:

# create zip of the dependency packages
zip -r $layer_package_file python

# remove temporary folder
rm -rf ./python/

# copy the package to an S3 bucket
 
aws s3 cp ./$layer_package_file s3://$bucket_name/


# create a lambda layer

aws lambda publish-layer-version \
  --layer-name  $layer_name \
  --description $layer_description \
  --content S3Bucket=$bucket_name,S3Key=$layer_package_file \
  --compatible-runtimes python3.13 \
  --compatible-architectures arm64