# 易站智能建站系统数据库迁移计划
## 旧数据库（easykai.db）升级修复完整方案

**版本**：v1.0  
**创建时间**：2026-07-07  
**适用场景**：以旧数据库（easykai.db）为基础，参考新数据库（verorun.db）结构，执行增量式表结构升级

---

## 一、核心目标与原则

### 1.1 核心目标
以 **旧数据库（easykai.db）** 为基础（保留全部种子数据、管理员账号、业务数据），通过对比 **新数据库（verorun.db）** 的表结构，执行**增量式表结构升级**，使旧库拥有与新库完全一致的表结构，但数据完全保留。

### 1.2 核心原则（从今日失败中总结）
1. **绝不直接替换数据库文件** —— 旧库是基础，新库仅作结构参考
2. **只做增量，不做删除** —— 优先新增表/列，不删除任何旧库已有表（除非明确确认是废弃表）
3. **操作前必须备份** —— 每一步破坏性操作前都要有可回滚的备份
4. **本地验证通过后再上线** —— 先在本地 easykai.db 上完整跑通，再同步到服务器
5. **先表后数据再索引** —— 按"表结构→种子数据→索引约束"的顺序执行

### 1.3 涉及文件
- **本地旧数据库**：`F:\Sites\VeroRun\data\easykai.db`（基础，需升级）
- **本地新数据库**：`F:\Sites\VeroRun\data\verorun.db`（参考，仅结构）
- **迁移脚本**：`F:\Sites\VeroRun\data\migrate_easykai_db.sql`（本计划生成的执行脚本）
- **差异报告**：`F:\Sites\VeroRun\data\db_schema_diff.md`（结构对比报告）

---

## 二、详细执行步骤

### 阶段 0：准备与备份

#### 步骤 0.1：备份旧数据库
```bash
# 在本地操作
cd F:\Sites\VeroRun\data
cp easykai.db easykai.db.bak_before_migration
```

#### 步骤 0.2：验证数据库完整性
```sql
-- 在 SQLite 命令行中执行
PRAGMA integrity_check;
-- 预期结果：返回 "ok"
```

#### 步骤 0.3：统计表数量
```sql
-- 旧库表数量
SELECT count(*) FROM sqlite_master WHERE type='table';

-- 新库表数量  
SELECT count(*) FROM sqlite_master WHERE type='table';
```

#### 步骤 0.4：记录关键信息
| 数据库 | 文件大小 | 表数量 | 完整性检查 |
|--------|----------|--------|------------|
| easykai.db (旧) | 记录大小 | 记录数量 | ok/not ok |
| verorun.db (新) | 记录大小 | 记录数量 | ok/not ok |

### 阶段 1：表结构对比分析

#### 步骤 1.1：导出两库表结构
```sql
-- 导出新库所有表的建表语句
SELECT name, sql FROM sqlite_master 
WHERE type='table' AND name NOT LIKE 'sqlite_%'
ORDER BY name;

-- 导出旧库所有表的建表语句（同上）
```

#### 步骤 1.2：生成差异报告
使用以下 Python 脚本进行自动对比（保存为 `compare_schema.py`）：

```python
import sqlite3
import json

def get_tables(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return tables

def compare_databases(old_db, new_db):
    old_tables = get_tables(old_db)
    new_tables = get_tables(new_db)
    
    # 找出差异
    only_in_new = set(new_tables.keys()) - set(old_tables.keys())
    only_in_old = set(old_tables.keys()) - set(new_tables.keys())
    in_both = set(old_tables.keys()) & set(new_tables.keys())
    
    # 结构不同的表
    different_structure = []
    for table in in_both:
        if old_tables[table] != new_tables[table]:
            different_structure.append(table)
    
    return {
        'only_in_new': list(only_in_new),
        'only_in_old': list(only_in_old),
        'different_structure': different_structure,
        'old_table_count': len(old_tables),
        'new_table_count': len(new_tables)
    }

if __name__ == '__main__':
    result = compare_databases('data/easykai.db', 'data/verorun.db')
    with open('data/db_schema_diff.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("对比完成，结果保存到 data/db_schema_diff.json")
```

#### 步骤 1.3：分析差异报告
根据对比结果，生成三类操作：
1. **需新增的表**：新库有，旧库没有
2. **需修改的表**：两库都有但结构不同
3. **需确认的表**：旧库有，新库没有（标记为待确认，不删除）

### 阶段 2：新增表（旧库中没有的表）

#### 步骤 2.1：按依赖顺序排序
先创建无外键依赖的表，后创建有外键依赖的表。

#### 步骤 2.2：生成建表 SQL
对于每个需新增的表，从新库提取建表语句：

```sql
-- 示例：新增 site_domains 表
CREATE TABLE site_domains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_name VARCHAR(255) NOT NULL,
    site_id INTEGER,
    is_primary BOOLEAN DEFAULT 0,
    ssl_certificate TEXT,
    ssl_expiry DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE
);
```

#### 步骤 2.3：执行建表（使用事务）
```sql
BEGIN TRANSACTION;

-- 逐个执行 CREATE TABLE 语句
CREATE TABLE table1 (...);
CREATE TABLE table2 (...);

COMMIT;
```

#### 步骤 2.4：插入种子数据（可选）
对于需要初始数据的表，从新库导出数据：

```sql
-- 导出新库数据
INSERT INTO site_domains (domain_name, site_id, is_primary) 
VALUES ('example.com', 1, 1);
```

### 阶段 3：修改表（两库都有但字段不同）

#### 情况 A：仅新增字段（简单情况）
```sql
ALTER TABLE 表名 ADD COLUMN 新字段名 字段类型 DEFAULT 默认值;
```

示例：
```sql
ALTER TABLE cms_posts ADD COLUMN publish_channels TEXT DEFAULT '[]';
ALTER TABLE users ADD COLUMN last_login_ip VARCHAR(45);
```

#### 情况 B：需要修改字段类型或删除字段（复杂情况）
SQLite 不支持直接修改或删除字段，需使用"重建表迁移法"：

```sql
-- 1. 旧表重命名
ALTER TABLE old_table RENAME TO old_table_backup;

-- 2. 按新结构建新表（使用新库的完整建表语句）
CREATE TABLE old_table (
    -- 新结构定义
);

-- 3. 迁移数据（只迁移共有的字段）
INSERT INTO old_table (id, name, email, created_at)
SELECT id, name, email, created_at 
FROM old_table_backup;

-- 4. 验证数据完整性
SELECT COUNT(*) FROM old_table;  -- 应与原表行数一致

-- 5. 删除备份表（验证无误后）
DROP TABLE old_table_backup;
```

#### 情况 C：需要处理默认值和约束
```sql
-- 新增字段时指定默认值
ALTER TABLE products ADD COLUMN is_featured BOOLEAN DEFAULT 0;

-- 新增字段时指定 NOT NULL（需确保已有数据有值或提供默认值）
ALTER TABLE orders ADD COLUMN payment_method VARCHAR(50) DEFAULT 'unknown' NOT NULL;
```

### 阶段 4：索引与约束

#### 步骤 4.1：对比索引
```sql
-- 查询两库索引
SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index';
```

#### 步骤 4.2：创建缺失索引
```sql
-- 示例：为用户表 email 字段创建唯一索引
CREATE UNIQUE INDEX idx_users_email ON users(email);

-- 示例：为文章表 created_at 字段创建索引
CREATE INDEX idx_cms_posts_created_at ON cms_posts(created_at);
```

#### 步骤 4.3：外键约束检查
```sql
-- 启用外键约束
PRAGMA foreign_keys = ON;

-- 检查外键约束
PRAGMA foreign_key_check;
```

### 阶段 5：数据一致性验证

#### 步骤 5.1：核心业务表验证
```sql
-- 检查关键表行数
SELECT 'users' as table_name, COUNT(*) as row_count FROM users
UNION ALL
SELECT 'admin_users', COUNT(*) FROM admin_users
UNION ALL
SELECT 'cms_posts', COUNT(*) FROM cms_posts
UNION ALL
SELECT 'products', COUNT(*) FROM products
UNION ALL
SELECT 'orders', COUNT(*) FROM orders;
```

#### 步骤 5.2：管理员账号验证
```sql
-- 验证管理员账号存在且可用
SELECT id, username, email, role FROM admin_users WHERE role = 'admin';
```

#### 步骤 5.3：业务逻辑验证
```sql
-- 验证外键关系
SELECT * FROM site_domains WHERE site_id NOT IN (SELECT id FROM sites);

-- 验证必填字段
SELECT * FROM users WHERE email IS NULL OR email = '';
```

### 阶段 6：本地应用联调验证

#### 步骤 6.1：启动本地服务
```bash
# 启动 admin 服务（使用升级后的数据库）
cd F:\Sites\VeroRun\admin
python app.py
```

#### 步骤 6.2：功能测试清单
| 测试项 | 预期结果 | 验证方法 |
|--------|----------|----------|
| 管理员登录 | 成功登录 | 输入管理员账号密码 |
| Site Domains 页面 | 正常显示，无 Connection Failed | 访问 `/admin/site-domains` |
| Navigation Settings | 正常显示，无 500 错误 | 访问 `/admin/navigation` |
| Coupon Management | 正常显示，无 404 | 访问 `/plugin/coupons/admin/list` |
| 文章管理 | 正常显示，可增删改查 | 访问 `/admin/cms/posts` |
| 用户管理 | 正常显示，可增删改查 | 访问 `/admin/users` |

#### 步骤 6.3：数据库操作测试
```sql
-- 测试新增数据
INSERT INTO site_domains (domain_name, site_id, is_primary) 
VALUES ('test.easykai.cn', 1, 0);

-- 测试更新数据
UPDATE cms_posts SET title = '测试标题' WHERE id = 1;

-- 测试删除数据（谨慎）
DELETE FROM test_table WHERE id = 999;
```

### 阶段 7：上线部署

#### 步骤 7.1：服务器备份
```bash
# 登录服务器
ssh easykai@***REMOVED***

# 备份当前数据库
cd /home/easykai/easykai-workspace/easykai.cn/data
cp x7k2m9a4.db x7k2m9a4.db.bak_$(date +%Y%m%d_%H%M%S)
```

#### 步骤 7.2：上传升级后的数据库
```bash
# 本地操作：上传数据库文件
rsync -avz --progress F:\Sites\VeroRun\data\easykai.db easykai@***REMOVED***:/home/easykai/easykai-workspace/easykai.cn/data/easykai_migrated.db

# 注意：绝对不能使用 --delete 参数，避免删除其他文件
```

#### 步骤 7.3：服务器替换操作
```bash
# 服务器操作：停止服务
cd /home/easykai/easykai-workspace/easykai.cn
./stop_all_services.sh

# 替换数据库文件（先备份原文件）
mv data/x7k2m9a4.db data/x7k2m9a4.db.backup
mv data/easykai_migrated.db data/x7k2m9a4.db

# 启动服务
./start_all_services.sh
```

#### 步骤 7.4：服务健康检查
```bash
# 检查各服务端口
netstat -tlnp | grep -E '8081|8083|8084'

# 查看服务日志
tail -f logs/admin.log
tail -f logs/auth-center.log
tail -f logs/platform.log
```

#### 步骤 7.5：线上功能验证
重复阶段6的测试清单，在线上环境验证。

---

## 三、风险控制与回滚方案

### 3.1 风险矩阵
| 风险点 | 概率 | 影响 | 预防措施 | 检测方法 |
|--------|------|------|----------|----------|
| 升级过程中数据库损坏 | 中 | 高 | 每阶段前备份，使用事务 | PRAGMA integrity_check |
| 表重建时数据丢失 | 中 | 高 | 先验证再删除备份表 | 行数对比，数据抽样 |
| 新字段缺少默认值 | 高 | 中 | 新增字段一律加 DEFAULT | 查询 NULL 值记录 |
| 外键约束失败 | 中 | 中 | 按依赖顺序建表 | PRAGMA foreign_key_check |
| 服务启动失败 | 中 | 高 | 本地完整验证 | 服务日志，端口检查 |

### 3.2 回滚方案
#### 情况一：升级过程中失败
```bash
# 恢复最近备份
cp easykai.db.bak_before_migration easykai.db

# 验证恢复
PRAGMA integrity_check;
```

#### 情况二：上线后发现问题
```bash
# 服务器回滚
./stop_all_services.sh
mv data/x7k2m9a4.db data/x7k2m9a4.db.failed
mv data/x7k2m9a4.db.backup data/x7k2m9a4.db
./start_all_services.sh
```

### 3.3 监控指标
| 指标 | 正常范围 | 检查频率 | 报警阈值 |
|------|----------|----------|----------|
| 数据库文件大小 | 50MB+ | 每小时 | < 1MB |
| 服务响应时间 | < 500ms | 每分钟 | > 2000ms |
| 错误率 | < 1% | 每分钟 | > 5% |
| 内存使用率 | < 80% | 每分钟 | > 90% |

---

## 四、今日失败教训（必须避免）

### 4.1 绝对禁止的操作
1. ❌ **严禁直接用新数据库文件覆盖旧数据库**
2. ❌ **严禁未备份就执行 DROP TABLE / DELETE**
3. ❌ **严禁未在本地验证就直接上传服务器**
4. ❌ **严禁部署脚本包含 data/ 目录**
5. ❌ **严禁一次性批量删除"看起来废弃"的表**

### 4.2 必须遵循的流程
1. ✅ **备份** → 小步操作 → 验证 → 下一步
2. ✅ 先方案后执行，确认再动手
3. ✅ 本地必验证，通过再上线
4. ✅ 一次只改一点，验证通过再继续

### 4.3 检查清单（每次操作前）
- [ ] 备份是否已创建且验证？
- [ ] 方案是否已输出并获得确认？
- [ ] 本地验证是否通过？
- [ ] 回滚方案是否明确？
- [ ] 影响范围是否评估？

---

## 五、附录

### 5.1 常用 SQLite 命令
```sql
-- 查看所有表
.tables

-- 查看表结构
.schema 表名

-- 查看索引
.indices 表名

-- 导入 SQL 文件
.read filename.sql

-- 导出数据库
.output filename.sql
.dump
```

### 5.2 关键表清单（必须验证）
1. **用户相关**：`users`, `admin_users`, `user_profiles`
2. **内容管理**：`cms_posts`, `cms_categories`, `cms_tags`
3. **导航系统**：`header_nav`, `header_links`, `footer_nav`, `footer_links`
4. **站点配置**：`sites`, `site_domains`, `site_settings`
5. **插件系统**：`plugins`, `plugin_settings`
6. **订单系统**：`products`, `orders`, `order_items`
7. **优惠券**：`coupons`, `coupon_redemptions`

### 5.3 联系人与应急响应
| 角色 | 联系方式 | 职责 |
|------|----------|------|
| 主负责人 | 内部通讯 | 整体协调，决策 |
| 数据库专家 | 内部通讯 | 数据库操作，故障处理 |
| 运维工程师 | 内部通讯 | 服务部署，监控 |
| 开发工程师 | 内部通讯 | 代码验证，功能测试 |

---

**文档状态**：✅ 已完成  
**下一步**：执行阶段0-阶段2，生成具体的迁移脚本