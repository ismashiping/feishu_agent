# 从零理解全文RAG

## 是什么
RAG先找到证据，再让模型利用证据回答。摘要适合筛论文，全文方法和结果段落才能支持更细的实验设计说明。OpenAlex只提供元数据和来源链接，OA不等于任意再利用许可。

## 为什么需要
同一DOI论文不应每问一次就下载、编码；先选文档，再在文档内召回段落可减少无关上下文与开销。缓存也必须保留章节、页码和hash，否则引用难以核对。

## 原理
先按is_oa和明确许可选择可信来源，核验HTTPS主机与重定向，再按DOI/题名确认文件身份。结构化JATS保留sec层级，PDF保留页号；清洗后source_units形成稳定解析表示，字符位置针对这个表示，不是PDF二进制字节。表格行列不直接粘连成数字证据。

SentenceSplitter在章节/页内切300-token块，重叠30；E5使用passage前缀编码入pgvector，问题用query前缀编码。每文档召回8段，按向量与实际问题词覆盖的加权RRF取2。无有效英文词时保持多语言向量顺序，不硬编码疾病。

## 缓存
paper_key优先规范DOI；signature记录解析/分块/模型版本；content_hash记录原响应，representation_hash记录清洗后的source_units。TTL到期重取后，如果表示未变则只续期，不因OAI响应时间改变而重复编码。索引和全部向量在一个事务内替换，失败回滚。

## 设计取舍
复用FulltextService、HTTPX、pypdf、defusedxml、LlamaIndex和E5，不建新Agent。独立OA表保留旧PMID缓存。首批许可/域名白名单限制覆盖；OCR、版面表格重建和复杂爬虫未纳入范围。失败保留摘要并记录真实原因。
