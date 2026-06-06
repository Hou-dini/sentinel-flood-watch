---
name: gcp-wif-github-setup
description: "Configure Google Cloud Workload Identity Federation (WIF) with GitHub Actions for passwordless, keyless authentication and deployment to GCP (e.g., Cloud Run, GKE, GCS)"
metadata:
  revision: 1
  updated-on: "2026-06-06"
  source: maintainer
  tags: "gcp,workload-identity-federation,wif,github-actions,oidc,security,ci-cd"
  license: "Apache-2.0"
  author: "Elikplim Kudowor (Hou-dini)"
---

# Google Cloud Workload Identity Federation (WIF) for GitHub Actions

This skill provides step-by-step instructions for establishing a secure, keyless authentication mechanism between GitHub Actions and Google Cloud Platform (GCP) using Workload Identity Federation (OIDC).

---

## Why Use Workload Identity Federation?

Traditionally, GitHub Actions deployed to GCP by exporting a JSON key for a Service Account and storing it as a GitHub Secret. This has several drawbacks:
- **Security Risk**: If the key is leaked, anyone can access your GCP resources.
- **Maintenance Burden**: Keys expire and must be rotated regularly.
- **Lack of Granularity**: A service account key gives access to any client holding it, making it hard to restrict based on repository metadata.

**Workload Identity Federation (WIF)** replaces static keys with short-lived tokens generated dynamically by Google's Security Token Service (STS) after validating GitHub's OpenID Connect (OIDC) identity token.

---

## Step 1: Define Your Setup Variables

Before running commands, set the following configuration variables in your shell. Replace the placeholders with your actual GCP and GitHub project details.

### PowerShell Setup
```powershell
$PROJECT_ID = "YOUR_GCP_PROJECT_ID"
$SERVICE_ACCOUNT_NAME = "YOUR_SERVICE_ACCOUNT_NAME"
$REPO = "YOUR_GITHUB_OWNER/YOUR_GITHUB_REPO" # e.g., "Hou-dini/sentinel-flood-watch"
$POOL_NAME = "github-pool"
$PROVIDER_NAME = "github-provider"
```

### Bash Setup
```bash
export PROJECT_ID="YOUR_GCP_PROJECT_ID"
export SERVICE_ACCOUNT_NAME="YOUR_SERVICE_ACCOUNT_NAME"
export REPO="YOUR_GITHUB_OWNER/YOUR_GITHUB_REPO" # e.g., "Hou-dini/sentinel-flood-watch"
export POOL_NAME="github-pool"
export PROVIDER_NAME="github-provider"
```

---

## Step 2: Configure Google Cloud Identity Resources

Authenticate with the Google Cloud CLI before executing these commands:
```bash
gcloud auth login
```

### 2.1 Enable the IAM Credentials API
This API allows GCP to generate short-lived credentials (tokens) for impersonating service accounts.
```bash
gcloud services enable iamcredentials.googleapis.com --project="${PROJECT_ID}"
```

### 2.2 Create the Workload Identity Pool
Create a global pool that organizes identity providers for your organization or project.
```bash
gcloud iam workload-identity-pools create $POOL_NAME \
    --project=$PROJECT_ID \
    --location="global" \
    --display-name="GitHub Actions Pool"
```

### 2.3 Create the OIDC Identity Provider
This registers GitHub as an Identity Provider (IdP) in your pool. It defines the mapping between GitHub's OIDC assertion claims and Google security attributes.
```bash
gcloud iam workload-identity-pools providers create-oidc $PROVIDER_NAME \
    --project=$PROJECT_ID \
    --location="global" \
    --workload-identity-pool=$POOL_NAME \
    --display-name="GitHub Provider" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner"
```

### 2.4 Fetch Your GCP Project Number
WIF resources must be referenced using the **numerical Project Number**, not the alphanumeric Project ID. Fetch it using this command:
```bash
gcloud projects describe $PROJECT_ID --format="value(projectNumber)"
```
> [!IMPORTANT]
> Save the numerical project number output. We will refer to it as `PROJECT_NUMBER` in subsequent steps.

### 2.5 Bind the GitHub Repository Identity to the Service Account
Authorize workflows running on your specific GitHub repository to impersonate the target deployment Service Account.

Replace `<PROJECT_NUMBER>` with the number fetched in the previous step:
```bash
gcloud iam service-accounts add-iam-policy-binding "${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --project=$PROJECT_ID \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/github-pool/attribute.repository/${REPO}"
```

---

## Step 3: Configure GitHub Repository Settings

Expose the GCP Workload Identity details to your GitHub Actions environment.

### 3.1 Construct the Provider URI
Use the project number and pool/provider names to build the Workload Identity Provider resource URI:
```
projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/github-pool/providers/github-provider
```

### 3.2 Add GitHub Secrets or Variables
In your GitHub Repository, navigate to **Settings > Secrets and variables > Actions** and add the following keys under the **Secrets** (or **Variables**) tab:

1. **`GCP_WIF_PROVIDER`**: Set this to the Workload Provider URI generated in Step 3.1.
2. **`GCP_WIF_SERVICE_ACCOUNT`**: Set this to the email address of the service account to impersonate (e.g., `YOUR_SERVICE_ACCOUNT_NAME@YOUR_GCP_PROJECT_ID.iam.gserviceaccount.com`).

---

## Step 4: Update the GitHub Actions Workflow

In your GitHub repository, update your workflow YAML file (typically `.github/workflows/ci.yml` or `deploy.yml`) to use the WIF credentials.

### 4.1 Set Job Permissions
GitHub Actions requires `id-token: write` permission to request the OIDC token from GitHub's OIDC provider.
```yaml
permissions:
  contents: 'read'
  id-token: 'write'
```
> [!NOTE]
> You can set this permission globally or specifically under the deployment job.

### 4.2 Configure the Google Auth Action
Update your auth step to reference the WIF secrets/variables:
```yaml
      - name: Google Auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.GCP_WIF_PROVIDER }}
          service_account: ${{ secrets.GCP_WIF_SERVICE_ACCOUNT }}
```

### Complete Deployment Job Example
```yaml
  deploy:
    name: Deploy Application
    runs-on: ubuntu-latest
    permissions:
      contents: 'read'
      id-token: 'write'

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Google Auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.GCP_WIF_PROVIDER }}
          service_account: ${{ secrets.GCP_WIF_SERVICE_ACCOUNT }}

      # Authenticated steps below...
      - name: Deploy to Cloud Run
        uses: google-github-actions/deploy-cloudrun@v2
        with:
          service: my-service
          region: us-central1
          source: ./
```

---

## Troubleshooting & Common Pitfalls

### 1. `Permission 'iam.serviceAccounts.getAccessToken' denied on resource`
- **Cause**: The IAM policy binding was not applied correctly or the attributes mapped do not match.
- **Fix**: Check if the project number in the `principalSet` string is correct and that the GitHub repository path (`owner/repo`) matches exactly, including case sensitivity.

### 2. `id-token: write` permission missing
- **Cause**: The workflow runner does not have permission to request the OIDC token from GitHub.
- **Fix**: Verify that you added `id-token: write` to the job or workflow permissions. Note that setting `permissions:` on a job overrides any global permissions, so make sure to include `contents: read` as well so checkout works.

### 3. Subject/Issuer mismatches
- **Cause**: The OIDC issuer URL in Google Cloud is not set to `https://token.actions.githubusercontent.com`.
- **Fix**: Re-create or update the OIDC provider to use the correct issuer URI. Do not add a trailing slash to the issuer URI.

### 4. `INVALID_ARGUMENT: The attribute condition must reference one of the provider's claims`
- **Cause**: Your Google Cloud Organization has an active policy constraint (`constraints/iam.workloadIdentityPoolProviderAttributeCondition`) that restricts creating Workload Identity Pool Providers without an attribute condition.
- **Fix**: Add the `--attribute-condition` flag to your `create-oidc` command, restricting access to your specific repository. E.g.:
  ```bash
  --attribute-condition="assertion.repository == 'owner/repo'"
  ```
