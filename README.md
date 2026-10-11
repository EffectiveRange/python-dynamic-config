# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/EffectiveRange/python-dynamic-config/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                            |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|-------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| dynamic\_config/\_\_init\_\_.py |        5 |        0 |        0 |        0 |    100% |           |
| dynamic\_config/cache.py        |       26 |       12 |        0 |        0 |     54% |10, 17-20, 23, 26, 31, 34, 37, 42, 45 |
| dynamic\_config/config.py       |       39 |       20 |        2 |        0 |     46% |20-22, 25, 28, 33, 36, 39, 42-43, 46, 57-59, 62, 65, 68-73 |
| dynamic\_config/parser.py       |       74 |        6 |       28 |        4 |     86% |84-\>79, 90-\>93, 99-\>102, 112-119 |
| dynamic\_config/source.py       |       66 |        0 |        6 |        0 |    100% |           |
| dynamic\_config/watcher.py      |        3 |        1 |        0 |        0 |     67% |         3 |
| **TOTAL**                       |  **213** |   **39** |   **36** |    **4** | **80%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/EffectiveRange/python-dynamic-config/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/EffectiveRange/python-dynamic-config/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/EffectiveRange/python-dynamic-config/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/EffectiveRange/python-dynamic-config/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2FEffectiveRange%2Fpython-dynamic-config%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/EffectiveRange/python-dynamic-config/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.