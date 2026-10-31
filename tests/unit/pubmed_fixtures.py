"""Synthetic PubMed XML for local ingestion and snapshot tests; not research evidence."""


def article(pmid="123", abstract=True):
    text = (
        '<Abstract><AbstractText Label="RESULTS">A <i>mixed</i> result.</AbstractText></Abstract>'
        if abstract
        else ""
    )
    return f"""<PubmedArticle><MedlineCitation><PMID>{pmid}</PMID><Article>
    <Journal><Title>Fixture Journal</Title><JournalIssue><PubDate>
    <Year>2020</Year><Month>Feb</Month></PubDate></JournalIssue></Journal>
    <ArticleTitle>Synthetic <i>title</i></ArticleTitle><AuthorList><Author>
    <CollectiveName>Study Group</CollectiveName></Author></AuthorList>
    {text}<PublicationTypeList><PublicationType UI="D016449">
    Randomized Controlled Trial</PublicationType></PublicationTypeList>
    </Article><CommentsCorrectionsList><CommentsCorrections RefType="ErratumIn">
    <PMID>456</PMID></CommentsCorrections></CommentsCorrectionsList>
    </MedlineCitation><PubmedData><ArticleIdList>
    <ArticleId IdType="pubmed">{pmid}</ArticleId></ArticleIdList>
    </PubmedData></PubmedArticle>"""


def xml(*records):
    return ("<PubmedArticleSet>" + "".join(records) + "</PubmedArticleSet>").encode()
