# Add `action-type` Input and Kernel Create/Update Modes to Deploy Course Action

> **Labels:** `enhancement` `jupyter` `enterprise-gateway` `docker` `gcp` `github-actions` `qbook`

---

## Feature Description

Restructure the `action.yaml` inputs so that `mode` (`create` / `update`) applies independently to **both** articles and kernels. A new `action-type` input (`article` / `kernel`) selects what is being operated on. The existing `article-type` (`course` / `blog`) continues to work exactly as before within the `article` action type.

The resulting input matrix is:

| `action-type` | `mode`    | `article-type` | What happens |
|---|---|---|---|
| `article`     | `create`  | `course`        | Create a new course *(existing behaviour)* |
| `article`     | `update`  | `course`        | Update an existing course *(existing behaviour)* |
| `article`     | `create`  | `blog`          | Create a new blog post *(existing behaviour)* |
| `article`     | `update`  | `blog`          | Update an existing blog post *(existing behaviour)* |
| `kernel`      | `create`  | —               | Build image → push to GCR → register new kernelspec on EG host → validate |
| `kernel`      | `update`  | —               | Rebuild image → push new tag to GCR → patch existing kernelspec on EG host → validate |

No existing workflow files break. `action-type` defaults to `article` so all current usage continues without any changes.

---

## Motivation

The current `mode` input conflates two independent concerns — *what* is being deployed (an article or a kernel) and *how* it is being deployed (creating for the first time or updating). Adding `action-type` cleanly separates these:

- Instructors already understand `mode: create` vs `mode: update` for courses. The same mental model should apply to kernels — create a kernel for the first time, or update an existing one with a new image.
- Keeping `article-type: course/blog` under `action-type: article` means zero changes for existing users.
- The kernel path needs its own `create` vs `update` distinction because the two operations are meaningfully different: `create` registers a brand-new kernelspec directory on the EG host, while `update` only patches the `image_name` in an existing `kernel.json` and pushes a new image tag — no EG restart needed for an update.

---

## Proposed Solution

### Input structure

```
action-type: article | kernel          ← NEW top-level switch (default: article)
  ├── mode: create | update            ← applies to both article and kernel independently
  ├── article-type: course | blog      ← only used when action-type is article
  └── kernel-name, gcr-*, eg-*, …     ← only used when action-type is kernel
```

### Step execution matrix

```
action-type=article, mode=create   →  validate course.json → verify notebooks → check images
                                       → create course → poll → notify

action-type=article, mode=update   →  validate course.json → verify notebooks → check images
                                       → update course → poll → notify

action-type=kernel,  mode=create   →  validate kernel inputs → build image → push to GCR
                                       → register NEW kernelspec on EG host
                                       → validate via qBraid API → smoke test → notify

action-type=kernel,  mode=update   →  validate kernel inputs → build image → push NEW tag to GCR
                                       → patch image_name in EXISTING kernelspec
                                       → validate via qBraid API → smoke test → notify
```

### `create` vs `update` for kernels

| | `mode: create` | `mode: update` |
|---|---|---|
| **Build image** | Yes — full build, tagged with commit SHA | Yes — rebuild with new tag |
| **Push to GCR** | Yes — new image + `:latest` | Yes — new tag + `:latest` |
| **kernelspec** | Install new directory on EG host via `jupyter-docker-spec install` | Patch `image_name` in existing `kernel.json` only |
| **EG restart** | Yes — new kernelspec must be picked up | No — running kernels are unaffected; new starts use the new image |
| **Validate + smoke test** | Yes | Yes |

### Outputs — separated by `action-type`

Outputs are written by a dedicated `emit-outputs` step that only fires for the matching `action-type`. This keeps article and kernel outputs strictly isolated — consumers never need to inspect `action-type` to know which outputs are valid.

**Article outputs** (only populated when `action-type: article`):

| Output | Description |
|---|---|
| `course_name` | Name of the deployed course |
| `course-custom-id` | Custom ID of the deployed course |
| `qbook_url` | Live URL of the deployed course on qBook |

**Kernel outputs** (only populated when `action-type: kernel`):

| Output | Description |
|---|---|
| `kernel-name` | Internal kernel name that was deployed |
| `kernel-display-name` | Display name registered on the EG host |
| `kernel-image` | Full GCR image reference including tag |

---

## Updated `action.yaml`

```yaml
name: 'Deploy Course to qBraid'
description: 'Validate, upload, and deploy a course, blog, or custom kernel to the qBraid platform'
author: 'qBraid'
branding:
  icon: 'upload-cloud'
  color: 'blue'

inputs:
  # ── Shared inputs ────────────────────────────────────────────────────────────
  api-key:
    description: 'qBraid API key (pass from secrets, e.g. secrets.QBRAID_API_KEY)'
    required: true
  repo-read-token:
    description: 'GitHub token with read access (pass from secrets, e.g. secrets.GITHUB_TOKEN)'
    required: true
  action-type:                                      # NEW
    description: 'What to deploy: "article" (course or blog) or "kernel"'
    required: false
    default: 'article'
  mode:
    description: 'Operation: "create" (first deploy) or "update" (redeploy). Applies to both articles and kernels.'
    required: false
    default: 'create'

  # ── Article inputs (used when action-type is article) ────────────────────────
  course-json-path:
    description: 'Path to course.json file'
    required: false
    default: 'course.json'
  article-type:
    description: 'Type of article: "course" or "blog"'
    required: false
    default: 'course'
  force-duplicate-questions:
    description: 'Whether to force duplicate questions'
    required: false
    default: 'false'
  draft:
    description: 'Whether to create a draft course (true or false)'
    required: false
    default: 'false'
  max-poll-attempts:
    description: 'Maximum polling attempts before timing out'
    required: false
    default: '20'
  poll-interval-seconds:
    description: 'Seconds to wait between polling attempts'
    required: false
    default: '15'
  max-consecutive-errors:
    description: 'Maximum consecutive polling errors before failing'
    required: false
    default: '5'
  course-custom-id:
    description: 'Custom ID of the course (required when action-type is article and mode is update)'
    required: false

  # ── Kernel inputs (used when action-type is kernel) ──────────────────────────
  kernel-name:
    description: 'Internal kernel name — folder name on EG host, matches kernelName in course.json'
    required: false
  kernel-display-name:
    description: 'Kernel display name in qBook — must match kernelId in course.json exactly'
    required: false
  kernel-dockerfile-path:
    description: 'Path to the kernel Dockerfile'
    required: false
    default: 'kernel/Dockerfile'
  gcr-region:
    description: 'GCP Artifact Registry region (e.g. asia-south1)'
    required: false
  gcr-project-id:
    description: 'GCP project ID'
    required: false
  gcr-repo:
    description: 'Artifact Registry repository name (e.g. course-kernels)'
    required: false
  gcr-image-name:
    description: 'Docker image name in the registry'
    required: false
  gcp-workload-identity-provider:
    description: 'GCP Workload Identity Federation provider resource name'
    required: false
  gcp-service-account:
    description: 'GCP service account email for Artifact Registry push'
    required: false
  eg-host:
    description: 'IP or hostname of the Jupyter Enterprise Gateway server'
    required: false
  eg-user:
    description: 'SSH username on the EG host'
    required: false
  eg-ssh-key:
    description: 'Private SSH key for EG host access'
    required: false
  eg-url:
    description: 'Full EG base URL (e.g. http://your-eg-host:8888)'
    required: false
  image-tag:
    description: 'Docker image tag override (default: short commit SHA)'
    required: false

outputs:
  # ── Article outputs (only populated when action-type is article) ─────────────
  course_name:
    description: 'Name of the deployed course'
    value: ${{ steps.emit-article-outputs.outputs.course_name }}
  course-custom-id:
    description: 'Custom ID of the deployed course'
    value: ${{ steps.emit-article-outputs.outputs.course_custom_id }}
  qbook_url:
    description: 'URL of the deployed course'
    value: ${{ steps.emit-article-outputs.outputs.qbook_url }}
  # ── Kernel outputs (only populated when action-type is kernel) ───────────────
  kernel-name:
    description: 'Internal kernel name that was deployed'
    value: ${{ steps.emit-kernel-outputs.outputs.kernel_name }}
  kernel-display-name:
    description: 'Display name registered on the EG host'
    value: ${{ steps.emit-kernel-outputs.outputs.kernel_display_name }}
  kernel-image:
    description: 'Full GCR image reference including tag'
    value: ${{ steps.emit-kernel-outputs.outputs.kernel_image }}

runs:
  using: "composite"
  steps:
    - name: Install UV
      uses: astral-sh/setup-uv@v4
      with:
        version: "latest"

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install dependencies
      shell: bash
      run: |
        uv pip install --system -e ${{ github.action_path }}

    - name: Validate required secrets
      shell: bash
      run: |
        if [[ -z "${{ inputs.api-key }}" ]]; then
          echo "::error::api-key is empty. Pass it from secrets (e.g. secrets.QBRAID_API_KEY)."
          exit 1
        fi
        if [[ -z "${{ inputs.repo-read-token }}" ]]; then
          echo "::error::repo-read-token is empty. Pass it from secrets (e.g. secrets.GITHUB_TOKEN)."
          exit 1
        fi

    # ── ARTICLE STEPS (action-type: article) ─────────────────────────────────

    - name: Stage 1 - Validate course.json structure
      id: validate-course
      if: inputs.action-type == 'article' || inputs.action-type == ''
      shell: bash
      run: |
        python ${{ github.action_path }}/src/scripts/validate_course.py "${{ inputs.course-json-path }}"

    - name: Stage 2 - Verify all notebooks exist
      if: inputs.action-type == 'article' || inputs.action-type == ''
      shell: bash
      run: |
        python ${{ github.action_path }}/src/scripts/verify_notebooks.py

    - name: Stage 3 - Verify all image references in notebooks
      if: inputs.action-type == 'article' || inputs.action-type == ''
      shell: bash
      run: |
        python ${{ github.action_path }}/src/scripts/check_images.py

    - name: Stage 4a - Create Article
      if: (inputs.action-type == 'article' || inputs.action-type == '') && inputs.mode == 'create'
      id: create-course
      shell: bash
      run: |
        python ${{ github.action_path }}/src/scripts/create_course.py \
          --api-key '${{ inputs.api-key }}' \
          --repo-read-token '${{ inputs.repo-read-token }}' \
          --repo-url '${{ github.server_url }}/${{ github.repository }}' \
          --commit-sha '${{ github.sha }}' \
          --article-type '${{ inputs.article-type }}' \
          --force-duplicate-questions '${{ inputs.force-duplicate-questions }}'

    - name: Stage 4b - Update Article
      if: (inputs.action-type == 'article' || inputs.action-type == '') && inputs.mode == 'update'
      id: update-course
      shell: bash
      run: |
        python ${{ github.action_path }}/src/scripts/update_course.py \
          --api-key '${{ inputs.api-key }}' \
          --course-custom-id '${{ inputs.course-custom-id }}' \
          --repo-read-token '${{ inputs.repo-read-token }}' \
          --repo-url '${{ github.server_url }}/${{ github.repository }}' \
          --commit-sha '${{ github.sha }}' \
          --article-type '${{ inputs.article-type }}' \
          --force-duplicate-questions '${{ inputs.force-duplicate-questions }}'

    - name: Stage 5 - Poll status for completion
      id: poll-status
      if: inputs.action-type == 'article' || inputs.action-type == ''
      shell: bash
      env:
        QBRAID_MAX_POLL_ATTEMPTS: ${{ inputs.max-poll-attempts }}
        QBRAID_POLL_INTERVAL_SECONDS: ${{ inputs.poll-interval-seconds }}
        QBRAID_MAX_CONSECUTIVE_ERRORS: ${{ inputs.max-consecutive-errors }}
      run: |
        COURSE_ID="${{ steps.create-course.outputs.course_custom_id }}${{ steps.update-course.outputs.course_custom_id }}"
        if [[ -z "$COURSE_ID" ]]; then
          echo "::error::course_custom_id is empty after create/update step."
          exit 1
        fi
        python ${{ github.action_path }}/src/scripts/poll_files_progress.py '${{ inputs.api-key }}' "$COURSE_ID"

    # ── KERNEL STEPS (action-type: kernel) ───────────────────────────────────

    - name: Kernel Stage 1 - Validate kernel inputs
      id: validate-kernel
      if: inputs.action-type == 'kernel'
      shell: bash
      run: |
        python ${{ github.action_path }}/src/scripts/validate_kernel_inputs.py \
          --kernel-name '${{ inputs.kernel-name }}' \
          --kernel-display-name '${{ inputs.kernel-display-name }}' \
          --dockerfile-path '${{ inputs.kernel-dockerfile-path }}' \
          --gcr-region '${{ inputs.gcr-region }}' \
          --gcr-project-id '${{ inputs.gcr-project-id }}' \
          --gcr-repo '${{ inputs.gcr-repo }}' \
          --gcr-image-name '${{ inputs.gcr-image-name }}' \
          --eg-host '${{ inputs.eg-host }}' \
          --eg-user '${{ inputs.eg-user }}'

    - name: Kernel Stage 2 - Authenticate to GCP
      if: inputs.action-type == 'kernel'
      uses: google-github-actions/auth@v2
      with:
        workload_identity_provider: ${{ inputs.gcp-workload-identity-provider }}
        service_account: ${{ inputs.gcp-service-account }}

    - name: Kernel Stage 3 - Build and push image to GCR
      id: build-kernel
      if: inputs.action-type == 'kernel'
      shell: bash
      run: |
        python ${{ github.action_path }}/src/scripts/build_push_kernel.py \
          --dockerfile-path '${{ inputs.kernel-dockerfile-path }}' \
          --gcr-region '${{ inputs.gcr-region }}' \
          --gcr-project-id '${{ inputs.gcr-project-id }}' \
          --gcr-repo '${{ inputs.gcr-repo }}' \
          --gcr-image-name '${{ inputs.gcr-image-name }}' \
          --image-tag '${{ inputs.image-tag || github.sha }}'

    - name: Kernel Stage 4a - Register new kernelspec on EG host
      id: register-kernel
      if: inputs.action-type == 'kernel' && inputs.mode == 'create'
      shell: bash
      run: |
        python ${{ github.action_path }}/src/scripts/register_kernelspec.py \
          --kernel-name '${{ inputs.kernel-name }}' \
          --kernel-display-name '${{ inputs.kernel-display-name }}' \
          --kernel-image '${{ steps.build-kernel.outputs.kernel_image }}' \
          --eg-host '${{ inputs.eg-host }}' \
          --eg-user '${{ inputs.eg-user }}' \
          --eg-ssh-key '${{ inputs.eg-ssh-key }}' \
          --restart-eg true

    - name: Kernel Stage 4b - Patch image in existing kernelspec
      id: patch-kernel
      if: inputs.action-type == 'kernel' && inputs.mode == 'update'
      shell: bash
      run: |
        python ${{ github.action_path }}/src/scripts/patch_kernelspec.py \
          --kernel-name '${{ inputs.kernel-name }}' \
          --kernel-display-name '${{ inputs.kernel-display-name }}' \
          --kernel-image '${{ steps.build-kernel.outputs.kernel_image }}' \
          --eg-host '${{ inputs.eg-host }}' \
          --eg-user '${{ inputs.eg-user }}' \
          --eg-ssh-key '${{ inputs.eg-ssh-key }}'

    - name: Kernel Stage 5 - Validate kernel via qBraid API
      if: inputs.action-type == 'kernel'
      shell: bash
      run: |
        python ${{ github.action_path }}/src/scripts/validate_kernel_availability.py \
          --api-key '${{ inputs.api-key }}' \
          --kernel-display-name '${{ inputs.kernel-display-name }}'

    - name: Kernel Stage 6 - Smoke test kernel via EG
      if: inputs.action-type == 'kernel'
      shell: bash
      run: |
        python ${{ github.action_path }}/src/scripts/smoke_test_kernel.py \
          --kernel-name '${{ inputs.kernel-name }}' \
          --eg-url '${{ inputs.eg-url }}'

    # ── EMIT OUTPUTS (separated by action-type) ──────────────────────────────

    # Article outputs — only written when action-type is article.
    # Kernel outputs block is untouched so consumers can safely check for emptiness.
    - name: Emit article outputs
      id: emit-article-outputs
      if: (inputs.action-type == 'article' || inputs.action-type == '') && success()
      shell: bash
      run: |
        {
          echo "course_name=${{ steps.validate-course.outputs.course_name }}"
          echo "course_custom_id=${{ steps.create-course.outputs.course_custom_id }}${{ steps.update-course.outputs.course_custom_id }}"
          echo "qbook_url=${{ steps.poll-status.outputs.qbook_url }}"
        } >> "$GITHUB_OUTPUT"

    # Kernel outputs — only written when action-type is kernel.
    # Article outputs block is untouched so consumers can safely check for emptiness.
    - name: Emit kernel outputs
      id: emit-kernel-outputs
      if: inputs.action-type == 'kernel' && success()
      shell: bash
      run: |
        {
          echo "kernel_name=${{ inputs.kernel-name }}"
          echo "kernel_display_name=${{ inputs.kernel-display-name }}"
          echo "kernel_image=${{ steps.build-kernel.outputs.kernel_image }}"
        } >> "$GITHUB_OUTPUT"

    # ── NOTIFICATIONS (shared, mode-aware) ───────────────────────────────────

    - name: Create deployment summary
      if: success()
      shell: bash
      run: |
        if [[ "${{ inputs.action-type }}" == "kernel" ]]; then
          cat >> $GITHUB_STEP_SUMMARY << 'DELIMITER'
        # 🧪 Kernel Deployment Successful

        **Kernel Name:** ${{ inputs.kernel-name }}
        **Display Name:** ${{ inputs.kernel-display-name }}
        **Mode:** ${{ inputs.mode }}
        **Image:** ${{ steps.build-kernel.outputs.kernel_image }}

        ## Next Steps

        Reference this kernel in your `course.json`:
        ```json
        "kernelName": "${{ inputs.kernel-name }}",
        "kernelId": "${{ inputs.kernel-display-name }}"
        ```
        DELIMITER
        else
          cat >> $GITHUB_STEP_SUMMARY << 'DELIMITER'
        # 🎉 Course Deployment Successful

        **Course Name:** ${{ steps.validate-course.outputs.course_name }}
        **Course Custom ID:** ${{ steps.create-course.outputs.course_custom_id }}${{ steps.update-course.outputs.course_custom_id }}
        **qBook URL:** ${{ steps.poll-status.outputs.qbook_url }}

        ## Next Steps

        You can now access your course at the qBook URL above.
        DELIMITER
        fi

    - name: Send notification comment
      if: success()
      uses: actions/github-script@v7
      with:
        script: |
          const isKernel = '${{ inputs.action-type }}' === 'kernel';
          const mode = '${{ inputs.mode }}';
          const body = isKernel
            ? `🧪 **Kernel ${mode === 'create' ? 'Registration' : 'Update'} Complete!**\n\nKernel \`${{ inputs.kernel-display-name }}\` is registered and validated on qBraid.\n\n**Image:** \`${{ steps.build-kernel.outputs.kernel_image }}\`\n\nUse in \`course.json\`:\n\`\`\`json\n"kernelName": "${{ inputs.kernel-name }}",\n"kernelId": "${{ inputs.kernel-display-name }}"\n\`\`\``
            : `🎓 **Course Deployment Complete!**\n\nYour course is now live on qBraid.\n\n**View your course:** ${{ steps.poll-status.outputs.qbook_url }}\n\nCourse name: \`${{ steps.validate-course.outputs.course_name }}\`\n\nCourse Custom ID: \`${{ steps.create-course.outputs.course_custom_id }}${{ steps.update-course.outputs.course_custom_id }}\``;
          try {
            await github.rest.repos.createCommitComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              commit_sha: context.sha,
              body
            });
          } catch (error) {
            if (error.status === 403) {
              core.warning('Could not create commit comment due to missing permissions.');
            } else {
              core.warning(`Failed to send notification: ${error.message}`);
            }
          }

    - name: Send failure notification
      if: failure()
      uses: actions/github-script@v7
      with:
        script: |
          const isKernel = '${{ inputs.action-type }}' === 'kernel';
          const subject = isKernel ? 'Kernel Deployment' : 'Course Deployment';
          try {
            await github.rest.repos.createCommitComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              commit_sha: context.sha,
              body: `❌ **${subject} Failed**\n\nThe deployment to qBraid failed. Please check the [workflow logs](${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}) for details.`
            });
          } catch (error) {
            core.warning(`Failed to send notification: ${error.message}`);
          }
```

---

## New Scripts (`src/scripts/`)

The kernel path adds two scripts for `create` vs `update` — mirroring the existing `create_course.py` / `update_course.py` split.

### `register_kernelspec.py` — kernel `create`

First-time registration. Generates a new kernelspec directory on the EG host, pre-pulls the image, and restarts EG so the new kernel is immediately discoverable.

```python
import argparse, subprocess, os, json, tempfile
from pathlib import Path

def ssh(host, user, key_path, script):
    subprocess.run([
        "ssh", "-i", key_path, "-o", "StrictHostKeyChecking=no",
        f"{user}@{host}", "bash", "-c", script
    ], check=True)

def scp(src, host, user, key_path, dest):
    subprocess.run([
        "scp", "-i", key_path, "-o", "StrictHostKeyChecking=no",
        "-r", src, f"{user}@{host}:{dest}"
    ], check=True)

def write_key(raw_key: str) -> str:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False)
    f.write(raw_key)
    f.close()
    os.chmod(f.name, 0o600)
    return f.name

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kernel-name", required=True)
    ap.add_argument("--kernel-display-name", required=True)
    ap.add_argument("--kernel-image", required=True)
    ap.add_argument("--eg-host", required=True)
    ap.add_argument("--eg-user", required=True)
    ap.add_argument("--eg-ssh-key", required=True)
    ap.add_argument("--restart-eg", default="true")
    args = ap.parse_args()

    key_path = write_key(args.eg_ssh_key)
    region = args.kernel_image.split("-docker.pkg.dev")[0]

    with tempfile.TemporaryDirectory() as tmpdir:
        # Generate kernelspec via gateway_provisioners
        subprocess.run([
            "jupyter-docker-spec", "install",
            "--kernel-name", args.kernel_name,
            "--display-name", args.kernel_display_name,
            "--image-name", args.kernel_image,
            "--output-dir", tmpdir
        ], check=True)

        # Patch image_name to exact tagged image (not :latest)
        kj = Path(tmpdir) / args.kernel_name / "kernel.json"
        spec = json.loads(kj.read_text())
        spec["metadata"]["process_proxy"]["config"]["image_name"] = args.kernel_image
        kj.write_text(json.dumps(spec, indent=2))
        print(f"kernel.json:\n{kj.read_text()}")

        scp(str(Path(tmpdir) / args.kernel_name),
            args.eg_host, args.eg_user, key_path,
            "/usr/local/share/jupyter/kernels/")

    # Pre-pull + optional EG restart
    restart_cmd = "sudo systemctl restart jupyter-enterprise-gateway && sleep 5" \
                  if args.restart_eg == "true" else "echo 'Skipping EG restart'"
    ssh(args.eg_host, args.eg_user, key_path, f"""
        gcloud auth configure-docker {region}-docker.pkg.dev --quiet
        docker pull {args.kernel_image}
        {restart_cmd}
        curl -sf http://localhost:8888/api/kernelspecs \
          | python3 -c "import sys,json; ks=json.load(sys.stdin); print('Registered kernels:', list(ks['kernelspecs'].keys()))"
    """)

    github_output = os.environ.get("GITHUB_OUTPUT", "")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"kernel_name={args.kernel_name}\n")
            f.write(f"kernel_display_name={args.kernel_display_name}\n")

    print(f"✓ Kernel '{args.kernel_name}' registered on EG host")
    os.unlink(key_path)

if __name__ == "__main__":
    main()
```

---

### `patch_kernelspec.py` — kernel `update`

Updates an existing kernel without a full re-registration. Patches only the `image_name` field in the existing `kernel.json` on the EG host, then pre-pulls the new image. No EG restart required — the next kernel start will use the new image automatically.

```python
import argparse, subprocess, os, json, tempfile

def ssh(host, user, key_path, script):
    subprocess.run([
        "ssh", "-i", key_path, "-o", "StrictHostKeyChecking=no",
        f"{user}@{host}", "bash", "-c", script
    ], check=True)

def write_key(raw_key: str) -> str:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False)
    f.write(raw_key)
    f.close()
    os.chmod(f.name, 0o600)
    return f.name

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kernel-name", required=True)
    ap.add_argument("--kernel-display-name", required=True)
    ap.add_argument("--kernel-image", required=True)
    ap.add_argument("--eg-host", required=True)
    ap.add_argument("--eg-user", required=True)
    ap.add_argument("--eg-ssh-key", required=True)
    args = ap.parse_args()

    key_path = write_key(args.eg_ssh_key)
    region = args.kernel_image.split("-docker.pkg.dev")[0]
    kernel_json_path = f"/usr/local/share/jupyter/kernels/{args.kernel_name}/kernel.json"

    # Patch image_name in-place on the EG host using Python — no scp needed
    ssh(args.eg_host, args.eg_user, key_path, f"""
        python3 - << 'PYEOF'
import json
path = "{kernel_json_path}"
with open(path) as f:
    spec = json.load(f)
spec["metadata"]["process_proxy"]["config"]["image_name"] = "{args.kernel_image}"
with open(path, "w") as f:
    json.dump(spec, f, indent=2)
print("Patched kernel.json:")
print(json.dumps(spec["metadata"]["process_proxy"]["config"], indent=2))
PYEOF
        gcloud auth configure-docker {region}-docker.pkg.dev --quiet
        docker pull {args.kernel_image}
        echo "✓ Image pre-pulled — next kernel start will use {args.kernel_image}"
    """)

    github_output = os.environ.get("GITHUB_OUTPUT", "")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"kernel_name={args.kernel_name}\n")
            f.write(f"kernel_display_name={args.kernel_display_name}\n")

    print(f"✓ Kernel '{args.kernel_name}' updated — no EG restart required")
    os.unlink(key_path)

if __name__ == "__main__":
    main()
```

---

## Example Workflows (`examples/`)

### Existing — `workflow.yml` (unchanged, shown for reference)

```yaml
- name: Deploy course
  uses: qbraid/deploy-course-action@v1
  with:
    action-type: article          # default — no change needed for existing users
    mode: create
    article-type: course
    api-key: ${{ secrets.QBRAID_API_KEY }}
    repo-read-token: ${{ secrets.GITHUB_TOKEN }}
```

### New — `kernel-create.yml`

```yaml
name: Create Kernel on qBraid

on:
  workflow_dispatch:

jobs:
  create-kernel:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write

    steps:
      - uses: actions/checkout@v4

      - name: Create kernel
        uses: qbraid/deploy-course-action@v1
        with:
          action-type: kernel
          mode: create                              # registers new kernelspec + restarts EG
          api-key: ${{ secrets.QBRAID_API_KEY }}
          repo-read-token: ${{ secrets.GITHUB_TOKEN }}
          kernel-name: qbraid_python
          kernel-display-name: "QBraid Python"     # must match kernelId in course.json
          kernel-dockerfile-path: kernel/Dockerfile
          gcr-region: asia-south1
          gcr-project-id: ${{ secrets.GCP_PROJECT_ID }}
          gcr-repo: course-kernels
          gcr-image-name: qbraid-python-kernel
          gcp-workload-identity-provider: ${{ secrets.GCP_WORKLOAD_IDENTITY_PROVIDER }}
          gcp-service-account: ${{ secrets.GCP_SERVICE_ACCOUNT }}
          eg-host: ${{ secrets.EG_HOST }}
          eg-user: ${{ secrets.EG_USER }}
          eg-ssh-key: ${{ secrets.EG_SSH_KEY }}
          eg-url: ${{ secrets.EG_URL }}
```

### New — `kernel-update.yml`

```yaml
name: Update Kernel on qBraid

on:
  push:
    branches: [main]
    paths:
      - 'kernel/**'
  workflow_dispatch:

jobs:
  update-kernel:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write

    steps:
      - uses: actions/checkout@v4

      - name: Update kernel
        uses: qbraid/deploy-course-action@v1
        with:
          action-type: kernel
          mode: update                              # patches image_name only — no EG restart
          api-key: ${{ secrets.QBRAID_API_KEY }}
          repo-read-token: ${{ secrets.GITHUB_TOKEN }}
          kernel-name: qbraid_python
          kernel-display-name: "QBraid Python"
          kernel-dockerfile-path: kernel/Dockerfile
          gcr-region: asia-south1
          gcr-project-id: ${{ secrets.GCP_PROJECT_ID }}
          gcr-repo: course-kernels
          gcr-image-name: qbraid-python-kernel
          gcp-workload-identity-provider: ${{ secrets.GCP_WORKLOAD_IDENTITY_PROVIDER }}
          gcp-service-account: ${{ secrets.GCP_SERVICE_ACCOUNT }}
          eg-host: ${{ secrets.EG_HOST }}
          eg-user: ${{ secrets.EG_USER }}
          eg-ssh-key: ${{ secrets.EG_SSH_KEY }}
          eg-url: ${{ secrets.EG_URL }}
```

---

## Alternatives Considered

**Keep a single `mode` input and use values like `kernel-create` / `kernel-update`** — rejected. Combining two concepts into one string makes the input harder to document and breaks the existing `create`/`update` mental model that users already know from the article workflow.

**Separate `action.yaml` files for article and kernel** — rejected. Two actions would duplicate the shared setup steps (UV install, Python, secret validation, notifications) and require users to maintain two action references in their repos.

**Implicit detection — infer `action-type` from which inputs are present** — rejected. Explicit is better than implicit for CI configuration. A missing `action-type` defaulting to `article` preserves backward compatibility without any guesswork.

---

## Additional Context

**Backward compatibility is fully preserved.** `action-type` defaults to `article`, so every existing workflow that omits it continues to work without any changes.

**`mode: update` for kernels does not restart EG.** Running kernel sessions are unaffected — they hold a reference to the container that was started with the previous image. Only new sessions started after the update will use the new image. This is intentional and matches how EG manages container lifecycle.

**`kernel-display-name` must exactly match `kernelId` in `course.json`** and `display_name` in `kernel.json` on the EG host. This is the string qBook sends to EG when a student opens a notebook.

### Related resources

- [Existing `examples/workflow.yml`](./examples/workflow.yml)
- [Jupyter Enterprise Gateway docs](https://jupyter-enterprise-gateway.readthedocs.io/)
- [gateway_provisioners](https://gateway-provisioners.readthedocs.io/)
- [google-github-actions/auth](https://github.com/google-github-actions/auth)
- [TESTING.md](../TESTING.md)