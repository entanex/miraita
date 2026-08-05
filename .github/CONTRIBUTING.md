# Miraita 贡献指南

首先，感谢你愿意为 Miraita 贡献自己的一份力量！

本指南旨在引导你更规范地向 Miraita 提交贡献，请务必认真阅读。

> 如果你喜欢这个项目，可以为本项目点亮⭐️，这是对我们最大的鼓励。

## 新贡献者指南

要了解项目概况，请阅读 [README](../README.md)。以下是一些帮助你开始第一次开源贡献的资源：

- [如何为开源做贡献](https://opensource.guide/zh-hans/how-to-contribute/)
- [寻找在 GitHub 上贡献开源的方法](https://docs.github.com/zh/get-started/exploring-projects-on-github/finding-ways-to-contribute-to-open-source-on-github)
- [设置 Git](https://docs.github.com/zh/get-started/quickstart/set-up-git)
- [GitHub 流](https://docs.github.com/zh/get-started/quickstart/github-flow)
- [协作处理拉取请求](https://docs.github.com/zh/pull-requests/collaborating-with-pull-requests)

## 让我们开始吧

### 议题

在提交 Issue 前，我们建议你先查看[已有的 Issues](https://github.com/entanex/miraita/issues)，以防重复提交。

#### 报告问题

如果你发现了一个问题，但是没有时间解决它，或者你不知道如何解决它，你可以创建一个议题。

#### 特性请求

如果你想要添加新的功能，你可以创建一个议题，并描述你想要的特性。

#### 帮助解决

浏览我们现有的议题，找到你感兴趣的议题。你可以使用标签作为过滤器缩小搜索范围。有关更多信息，请参见[标签](https://github.com/entanex/miraita/labels)。

如果你发现了需要解决的议题，请在议题下添加评论，以便我们知道你正在解决该议题。

### 进行更改

在修复 bug 之前，我们建议你检查是否存在描述 bug 的问题，因为这可能是一个文档问题，或者是否存在一些有助于了解的上下文。

如果你正在开发一个特性，那么我们要求你首先打开一个特性请求议题，以便与维护人员讨论是否需要该特性以及这些特性的设计。这有助于为维护人员和贡献者节省时间，并意味着可以更快地提供特性。

#### 在代码空间中进行更改

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/entanex/miraita)

有关代码空间的更多信息，请参阅 [GitHub Codespaces 概述](https://docs.github.com/zh/codespaces/overview)。

#### 在开发容器中进行更改

[![Open in Dev Containers](https://img.shields.io/static/v1?label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/entanex/miraita)

如果你已经安装了 VS Code 和 Docker，可以点击上面的徽标或 [这里](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/entanex/miraita) 开始使用。点击这些链接后，VS Code 将根据需要自动安装 Dev Containers 扩展，将源代码克隆到容器卷中，并启动一个开发容器以供使用。

#### 在本地环境中进行更改

如果你不想使用代码空间或者开发容器，你可以在本地环境中开发。

Miraita 使用 [uv](https://docs.astral.sh/uv/) 管理项目依赖。请确保你已经安装了 uv，然后在项目根目录下运行 `uv sync` 安装依赖。

下面的命令能在已安装 uv 的情况下帮你快速配置开发环境。

```bash
# 安装 python 依赖
uv sync --all-groups
# 安装 prek git hook
uv run prek install
```

### 提交修改

一旦对修改满意，就可以将其提交。别忘了进行自我审核和本地测试，以加快审核过程⚡。

请确保你的每一个 commit 都能清晰地描述其意图，一个 commit 尽量只有一个意图。

Miraita 的 commit message 格式遵循 [gitmoji](https://gitmoji.dev/) 规范，在创建 commit 时请牢记这一点。

### 创建拉取请求

完成修改后，创建一个拉取请求，也称为 PR。

- 拉取请求标题应尽量使用中文，以便自动生成更新日志。
- 填写拉取请求模板，以便我们审核你的 PR。该模板可帮助审核员了解你的更改以及你的拉取请求的目的。
- 如果你的 PR 修复或解决了现有问题，请[将拉取请求链接到议题](https://docs.github.com/zh/issues/tracking-your-work-with-issues/linking-a-pull-request-to-an-issue)。
- 在一个 PR 中有多个提交是可以的。你不需要重新变基或强制推送你的更改，因为我们将使用 Squash Merge 在合并时将你的提交压缩成一个提交。
- 最好提交多个涉及少量文件的拉取请求，而不是提交涉及多个文件的大型拉取请求。这样做可以使审核员更容易理解你的更改，并且可以更快地合并你的更改。
- 我们可能会要求在合并 PR 之前进行更改，或者使用[建议的更改](https://docs.github.com/zh/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/incorporating-feedback-in-your-pull-request)，或者拉请求注释。你可以通过 UI 直接应用建议的更改，也可以在 fork 中进行任何其他更改，然后将它们提交到分支。
- 当你更新 PR 并应用更改时，将每个对话标记为[已解决](https://docs.github.com/zh/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/commenting-on-a-pull-request#%E8%A7%A3%E5%86%B3%E5%AF%B9%E8%AF%9D)。
- 如果遇到任何合并问题，请查看[解决合并冲突](https://github.com/skills/resolve-merge-conflicts)，以帮助你解决合并冲突和其他问题。

## 风格指南

Miraita 的代码风格遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 与 [PEP 484](https://www.python.org/dev/peps/pep-0484/) 规范，请确保你的代码风格和项目已有的代码保持一致，变量命名清晰，代码类型完整，有适当的注释与测试代码。

## 版权声明

在为此项目做贡献时，请确保你的贡献内容不会侵犯他人的知识产权，否则你的贡献将被视为无效。

通过贡献你的代码、问题或建议，即表示你同意将你的贡献内容以开源的形式提供，并遵守项目所采用的开源许可证。
