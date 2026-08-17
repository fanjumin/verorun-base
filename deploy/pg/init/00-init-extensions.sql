-- VeroRun 主库初始化脚本（VR-PLG-003）
-- project_workspace 插件的 document_chunks.embedding 列依赖 pgvector 的 vector 类型。
-- 本脚本由 docker-entrypoint-initdb.d 在数据库首次初始化（空数据卷）时以超级用户执行。
-- 注意：已有数据卷/裸机部署需手动执行一次：CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS vector;
