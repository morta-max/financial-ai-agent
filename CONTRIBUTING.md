# 贡献指南 (Contributing Guide)

感谢你对 A-Share Financial AI Agent 的关注！我们欢迎任何形式的贡献。

## 如何贡献

### 🐛 报告 Bug

1. 在 [Issues](../../issues) 页检查是否已有相同问题
2. 如果不存在，创建新 Issue，包含：
   - **标题**: 简明描述问题
   - **描述**: 详细说明复现步骤、期望行为、实际行为
   - **环境**: Python 版本、操作系统、依赖版本
   - **截图/日志**: 如有

### 💡 功能建议

1. 在 Issues 中说明功能需求和使用场景
2. 描述期望的 API 或 UI 效果
3. 如有可能，提供参考实现或伪代码

### 🔧 提交代码

#### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/morta-max/financial-ai-agent.git
cd financial-ai-agent

# 安装后端依赖
cd backend
pip install -r requirements.txt

# 安装前端依赖
cd ../frontend
npm install

# 初始化数据库
cd ..
python scripts/init_db.py
```

#### 分支策略

- `master` — 稳定发布版本
- `dev` — 开发分支
- `feature/xxx` — 新功能分支
- `fix/xxx` — Bug 修复分支

#### 提交流程

```bash
# 1. 从 master 创建新分支
git checkout -b feature/your-feature

# 2. 编写代码和测试

# 3. 运行现有测试确保无回归
cd backend && python -m pytest tests/

# 4. 提交（使用约定式提交格式）
git commit -m "feat: 添加XXX功能"
# 或
git commit -m "fix: 修复XXX问题"

# 5. 推送并创建 Pull Request
git push origin feature/your-feature
```

#### 提交信息规范

使用 [约定式提交 (Conventional Commits)](https://www.conventionalcommits.org/) 格式：

| 前缀 | 用途 |
|------|------|
| `feat:` | 新功能 |
| `fix:` | Bug 修复 |
| `docs:` | 文档更新 |
| `style:` | 代码格式（不影响功能） |
| `refactor:` | 代码重构 |
| `perf:` | 性能优化 |
| `test:` | 测试相关 |
| `chore:` | 构建/工具/依赖 |

### 📋 Pull Request 清单

提交 PR 前请确认：

- [ ] 代码遵循项目现有风格
- [ ] 添加了必要的注释和文档字符串
- [ ] 新功能有对应的测试
- [ ] 所有测试通过
- [ ] 更新了相关文档
- [ ] 提交信息使用约定式提交格式

### 🏗 项目结构

```
financial-ai-agent/
├── backend/                    # Python 后端
│   ├── api/                    # FastAPI 服务
│   │   ├── main.py             # 路由与中间件
│   │   ├── validators.py       # 输入验证
│   │   └── middleware.py       # 速率限制/安全
│   ├── data/                   # 数据层
│   │   ├── akshare_client.py   # AKShare 数据获取
│   │   ├── duckdb_manager.py   # 数据库管理
│   │   └── sync_service.py     # 数据同步
│   ├── analysis/               # 分析引擎
│   │   ├── technical.py        # 技术指标
│   │   ├── fundamental.py      # 基本面分析
│   │   ├── risk.py             # 风险计算
│   │   └── valuation.py        # 估值分析
│   └── mcp_server/             # MCP 服务器
│       └── server.py           # 30+ AI 工具
├── frontend/                   # Next.js 前端
│   ├── app/                    # 页面与路由
│   └── components/             # UI 组件
│       ├── stocks/             # 股票相关组件
│       ├── market/             # 市场数据组件
│       ├── analysis/           # 分析组件
│       └── chat/               # 聊天组件
└── scripts/                    # 数据管道脚本
```

### 📊 推荐开发方向

- 🧠 **LLM 集成**: 接入 Claude/GPT 实现智能对话分析
- 📡 **更多数据源**: Tushare、Wind、同花顺 iFinD
- 📊 **量化策略**: 因子研究、回测引擎、信号生成
- 🔔 **预警系统**: 价格突破、异动监控、推送通知
- 🌐 **多市场**: 港股、美股、期货、期权
- 📱 **移动端**: React Native 或小程序

### ❓ 有问题？

- 查看 [Issues](../../issues) 或 [Discussions](../../discussions)
- 联系维护者: 2898532734@qq.com

---

再次感谢你的贡献！🎉
