# CI/CD Workflow Plan

The workflow will be named `CI` and run on `push` to `main`. It will contain two main jobs: `backend` and `frontend`.

## Workflow Structure

```mermaid
graph TD
    A[Push to main] --> B{Parallel Jobs}
    B --> C[Backend Job]
    B --> D[Frontend Job]
    C --> C1[Setup Python]
    C --> C2[Install Dependencies]
    C --> C3[Lint with Ruff]
    C --> C4[Test with Pytest]
    D --> D1[Setup Node.js]
    D --> D2[Install Dependencies]
    D --> D3[Lint with ESLint]
    D --> D4[Build Project]
```

## Proposed Steps

### Backend
1. Use `actions/setup-python`.
2. `pip install -r backend/requirements.txt` + `pytest` + `ruff`.
3. `ruff check backend`
4. `pytest backend`

### Frontend
1. Use `actions/setup-node`.
2. `npm install` inside `frontend` folder.
3. `npm run lint`
4. `npm run build`

Would you like to approve this structure or make changes?
