# Git 快速上手（给队友）

如果你不熟悉 Git，只需要先学会这份文档里的最小流程就够了。

## 你平时只需要记住这 5 条

1. 开工前先拉最新代码
2. 不要直接在 `main` 上写
3. 每次新任务都新建分支
4. 提交前先做本地检查
5. 不会合并就不要自己合并

## 最小操作流程

### 第一次下载仓库

```powershell
git clone https://github.com/AmalZhang/IMC_4.git
cd IMC_4
```

### 每次开始工作前

```powershell
git checkout main
git pull
```

### 新建自己的工作分支

```powershell
git checkout -b feat/r3-hydrogel
```

### 改完后检查

```powershell
python -m py_compile trader_round3.py round3_analysis.py
```

### 查看哪些文件改了

```powershell
git status
```

### 提交代码

```powershell
git add .
git commit -m "feat: improve hydrogel trading logic"
```

### 推送到远端

```powershell
git push -u origin feat/r3-hydrogel
```

### 如果你分析了平台测试日志

把对应日志目录也一起提交，例如：

```powershell
git add ROUND_3/logs/406001
git commit -m "chore: add Round 3 test logs 406001"
```

这样主线维护者和 Codex 可以基于同一份日志继续优化。

## 什么时候需要问主线维护者

下面这些情况不要自己硬处理：

- `git pull` 后出现冲突
- 你和别人同时改了 `trader_round3.py`
- 不确定该不该改 `main`
- 不确定这次改动是否值得合并

## 提交代码时顺手发的说明

建议每次提交后发一句：

```text
我在 feat/r3-hydrogel 分支上改了 HYDROGEL_PACK 的逻辑。
本地 py_compile 已通过。
这次主要目标是减少高位回撤。
```

## 最后记住一句话

不会 Git 没关系，但不要直接改 `main`。
