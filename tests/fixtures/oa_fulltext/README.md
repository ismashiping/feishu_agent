# 真实OA全文fixtures

这些文件来自公开论文并按记录中的CC BY许可作为解析与追溯工程样例。请保留原作者、题名、DOI、来源和许可声明；未经核验的表格或特殊字体不作为医学事实。合成测试中的句子明确为synthetic，不是论文结论。

- mri-record.json / mri-fulltext.xml / manifest.json：Preoperative evaluation of microvascular invasion in hepatocellular carcinoma with a radiological feature-based nomogram: a bi-centre study，DOI 10.1186/s12880-024-01206-7，PMC10821254；原始官方OAI响应，许可CC BY（具体版本见JATS声明），SHA256及获取时间见manifest。作者见mri-record.json。论文入口：https://doi.org/10.1186/s12880-024-01206-7 。
- plos-record.json / plos-fulltext.pdf / plos-pdf-manifest.json：Effect of Blood Vessel Segmentation on the Outcome of Electroporation-Based Treatments of Liver Tumors，DOI 10.1371/journal.pone.0125591；PLOS出版方原PDF，CC BY（具体版本以原文为准），作者见plos-record.json，原下载URL与SHA256见manifest。论文入口：https://doi.org/10.1371/journal.pone.0125591 。该论文是PDF工程对照，不因被下载就算当前用户问题的直接证据。
- search-provenance.json：第二阶段真实MRI-MVI查询的冻结来源记录，用于标注缓存回放的真实来历，不表示本阶段又执行了相同查询。

原XML/PDF文件没有清洗或重写；清洗仅产生运行期source_units表示。manifest绑定原字节，representation_hash绑定解析文本。再次采集应另建批次，不覆盖当前fixture。
