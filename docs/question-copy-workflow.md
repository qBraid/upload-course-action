# Copy questions into a GitHub-backed course

Use an agent with qBraid MCP and GitHub repository access to copy questions,
prepare a course PR, and deploy the reviewed commit. This procedure assumes the
API's question-copy feature is deployed.

## Save the copy result

1. Select the source questions and destination organization through MCP.
2. Call `copy_qbook_questions`. For course-based authorization, supply both
   `sourceCourseId` and `targetCourseId`.
3. Save the decoded JSON result to `.qbraid/question-copy.json` in the destination
   repository. Save only the result, without access tokens or HTTP headers.

The result contains a `questions` array. Each item includes `sourceCustomId`,
`customId`, and `type`. The helper also accepts a REST response with this array
under `data`. Retain the saved mapping for retries; do not copy again because a
repository edit or deployment failed.

## Prepare the destination PR

Check out a reviewed revision of `qBraid/upload-course-action` that includes
`src/scripts/prepare_question_copy.py`. Install that revision's Python
dependencies. Set `UPLOAD_ACTION_DIR` to the absolute path of that checkout.

From the destination course repository root:

1. Create a feature branch.
2. Add the source question widgets at the requested positions in the destination
   notebook. If you copied a whole lesson, its existing widgets already provide
   these positions. Put repeated widgets of the same type in separate cells.
3. Preview the reference changes:

   ```sh
   python "$UPLOAD_ACTION_DIR/src/scripts/prepare_question_copy.py" \
     --mapping .qbraid/question-copy.json
   ```

4. Apply the changes:

   ```sh
   python "$UPLOAD_ACTION_DIR/src/scripts/prepare_question_copy.py" \
     --mapping .qbraid/question-copy.json --write
   ```

5. Verify that all changes are applied:

   ```sh
   python "$UPLOAD_ACTION_DIR/src/scripts/prepare_question_copy.py" \
     --mapping .qbraid/question-copy.json --check
   ```

   Expect `"files": []`. Use the same command in PR validation. It does not
   authenticate, create backend questions, deploy, or modify files.

6. Review and commit the changed notebooks, complete `course.json`, and saved
   mapping. Open a PR that identifies the destination course and organization.

Use `--course-json path/to/course.json` for a nondefault manifest path. Notebook
paths remain relative to the repository root, matching the deployment Action.
The helper updates every occurrence of a mapped widget in notebooks listed by
that manifest. It preserves unrelated references and derives both MCQ and FRQ
placement lists. Existing CQ lists remain unchanged.

The helper refuses unused mappings and ambiguous mappings before writing. It
does not insert cells, select lesson positions, check backend permissions, or
verify that an unrelated question belongs to the destination organization. The
agent must verify destination question access before opening the PR.

## Deploy the reviewed commit

Merge the course PR and run its deployment workflow with:

- A pinned Action revision containing this helper and the reference-preserving
  validator. An older Action silently drops the reference fields.
- `mode: update` and the existing destination `course-custom-id`.
- The destination organization's API key from GitHub secrets.
- `force-duplicate-questions: 'false'`.
- `repo-read-token` with access to the destination repository.

For a dedicated API preview, set `QBRAID_API_BASE_URL` in the Action step's
environment to that preview's `/api/v1` URL. Point the qBook preview at the same
API preview. Keep the normal workflow on the intended production or staging API.

The Action must receive the complete course manifest. The helper-generated
`chapterQuestions` and `sectionQuestions` fields survive validation and make a
question-reference change visible to API redeployment detection. The processor
then regenerates the lesson JSON from the merged repository commit.

Open the deployed lesson and answer both copied question types. Rerun the
deployment and confirm IDs and points remain unchanged. A processed status by
itself does not prove the lesson renders.
