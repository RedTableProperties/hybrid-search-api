const { oas } = require("@stoplight/spectral-rulesets");

module.exports = {
  extends: [oas],
  rules: {
    "operation-operationId": "error",
    "operation-description": "error",
    "operation-tag-defined": "warn",
    "operation-success-response": "warn",
    "info-license": "off",
    "openapi-tags-alphabetical": "off",
  },
};