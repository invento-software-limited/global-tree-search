### Global Tree View


**Global Tree View** intercepts and enhances standard search suggestions for tree DocTypes in Frappe and ERPNext. It displays complete hierarchical paths (e.g., `Current Assets -> Bank Accounts -> Cash`) instead of just plain leaf node names, reducing selection errors in deep structures.

### 📖 Documentation

Check out the complete [Product Overview & User Guide](https://invento-software-limited.github.io/global-tree-search/) for detailed installation, configuration, and troubleshooting instructions.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/invento-software-limited/global-tree-search --branch main
bench install-app global_tree_view
```


### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/global_tree_view
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade
### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


### License

mit
