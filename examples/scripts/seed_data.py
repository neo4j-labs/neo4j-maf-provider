"""
Seed the Neo4j database with sample financial documents data.
Creates the same schema used by the Python samples:
  Company -[:FILED]-> Document <-[:FROM_DOCUMENT]- Chunk
  Company -[:FACES_RISK]-> RiskFactor
  Company -[:MENTIONS]-> Product

Also generates embeddings via Azure OpenAI and creates indexes.

Usage: python examples/scripts/seed_data.py
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Load .env from repo root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(REPO_ROOT / ".env")

from azure.identity import DefaultAzureCredential
from neo4j import GraphDatabase
from openai import AzureOpenAI

# --- Sample data -----------------------------------------------------------

COMPANIES = [
    {"name": "Apple Inc.", "ticker": "AAPL"},
    {"name": "Microsoft Corporation", "ticker": "MSFT"},
    {"name": "NVIDIA Corporation", "ticker": "NVDA"},
]

DOCUMENTS = [
    {"title": "Apple Inc. 10-K Annual Report 2024", "company": "Apple Inc."},
    {"title": "Microsoft Corporation 10-K Annual Report 2024", "company": "Microsoft Corporation"},
    {"title": "NVIDIA Corporation 10-K Annual Report 2024", "company": "NVIDIA Corporation"},
]

RISK_FACTORS = {
    "Apple Inc.": [
        {"name": "Supply Chain Disruption", "description": "Supply chain disruptions could materially impact product availability and revenue."},
        {"name": "Market Competition", "description": "Intense competition in the consumer electronics market may reduce market share."},
        {"name": "International Regulation", "description": "Regulatory changes in international markets could affect operations."},
    ],
    "Microsoft Corporation": [
        {"name": "Cybersecurity Threats", "description": "Cybersecurity threats and data breaches pose risks to customer trust."},
        {"name": "Technological Change", "description": "Rapid technological change requires continuous investment in R&D."},
        {"name": "Antitrust Regulation", "description": "Antitrust regulations could limit business practices and acquisitions."},
    ],
    "NVIDIA Corporation": [
        {"name": "Semiconductor Supply Chain", "description": "Dependence on semiconductor supply chains creates manufacturing risks."},
        {"name": "Export Controls", "description": "Export controls on advanced chips may limit revenue from key markets."},
        {"name": "AI Market Competition", "description": "AI market competition is intensifying from both startups and incumbents."},
    ],
}

PRODUCTS = {
    "Apple Inc.": ["iPhone", "MacBook", "iPad", "Apple Watch", "AirPods"],
    "Microsoft Corporation": ["Azure", "Microsoft 365", "Windows", "GitHub", "Teams"],
    "NVIDIA Corporation": ["GeForce RTX", "CUDA", "DGX Systems", "Omniverse", "Drive"],
}

CHUNKS = [
    # Apple chunks
    {
        "company": "Apple Inc.",
        "doc": "Apple Inc. 10-K Annual Report 2024",
        "text": "Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide. The company's flagship product, iPhone, generated approximately 52% of total revenue in fiscal year 2024.",
    },
    {
        "company": "Apple Inc.",
        "doc": "Apple Inc. 10-K Annual Report 2024",
        "text": "The company faces significant supply chain risks due to its reliance on a limited number of suppliers for critical components. Disruptions in the supply of semiconductor chips, OLED displays, or other key components could materially impact product availability and revenue.",
    },
    {
        "company": "Apple Inc.",
        "doc": "Apple Inc. 10-K Annual Report 2024",
        "text": "Apple continues to invest heavily in research and development, with R&D expenses reaching $29.9 billion in 2024. Key areas of investment include augmented reality, machine learning, and health technology integrated into Apple Watch and other wearable devices.",
    },
    {
        "company": "Apple Inc.",
        "doc": "Apple Inc. 10-K Annual Report 2024",
        "text": "Services revenue, including the App Store, Apple Music, iCloud, and Apple TV+, grew 14% year-over-year to reach $96 billion. The services segment now represents the second-largest revenue contributor after iPhone.",
    },
    # Microsoft chunks
    {
        "company": "Microsoft Corporation",
        "doc": "Microsoft Corporation 10-K Annual Report 2024",
        "text": "Microsoft Corporation develops and supports software, services, devices, and solutions worldwide. Azure cloud services revenue grew 29% year-over-year, driven by enterprise adoption of AI workloads and hybrid cloud solutions.",
    },
    {
        "company": "Microsoft Corporation",
        "doc": "Microsoft Corporation 10-K Annual Report 2024",
        "text": "Cybersecurity remains a critical risk factor. The company has experienced sophisticated nation-state attacks targeting its infrastructure. Microsoft has committed to investing over $20 billion in security improvements through its Secure Future Initiative.",
    },
    {
        "company": "Microsoft Corporation",
        "doc": "Microsoft Corporation 10-K Annual Report 2024",
        "text": "The acquisition of Activision Blizzard for $69 billion expanded Microsoft's gaming portfolio significantly. Xbox Game Pass subscribers exceeded 34 million, and the gaming division contributed $22 billion in annual revenue.",
    },
    {
        "company": "Microsoft Corporation",
        "doc": "Microsoft Corporation 10-K Annual Report 2024",
        "text": "Microsoft 365 commercial products and cloud services revenue increased 15% driven by growth in Office 365 Commercial and Microsoft Teams. GitHub surpassed 100 million developers and Copilot for Business saw rapid enterprise adoption.",
    },
    # NVIDIA chunks
    {
        "company": "NVIDIA Corporation",
        "doc": "NVIDIA Corporation 10-K Annual Report 2024",
        "text": "NVIDIA Corporation is a leader in accelerated computing, providing GPUs and system-on-chip units for gaming, professional visualization, data center, and automotive markets. Data center revenue surged 217% to $47.5 billion driven by AI training and inference demand.",
    },
    {
        "company": "NVIDIA Corporation",
        "doc": "NVIDIA Corporation 10-K Annual Report 2024",
        "text": "U.S. government export controls on advanced AI chips to China and other countries represent a material risk. The company estimates that export restrictions could reduce data center revenue by $5-8 billion annually if expanded further.",
    },
    {
        "company": "NVIDIA Corporation",
        "doc": "NVIDIA Corporation 10-K Annual Report 2024",
        "text": "NVIDIA's CUDA platform remains the dominant ecosystem for GPU-accelerated computing with over 4 million developers. The company's software and platform strategy creates significant switching costs and competitive moats.",
    },
    {
        "company": "NVIDIA Corporation",
        "doc": "NVIDIA Corporation 10-K Annual Report 2024",
        "text": "The company's DGX systems and networking products, including InfiniBand and Ethernet switches, are critical infrastructure for large-scale AI training clusters. Hyperscale customers account for approximately 50% of data center revenue.",
    },
]


def get_embeddings(client, texts, model="text-embedding-3-small"):
    """Generate embeddings for a list of texts in batches."""
    embeddings = []
    batch_size = 20
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        resp = client.embeddings.create(input=batch, model=model)
        embeddings.extend([d.embedding for d in resp.data])
    return embeddings


def main():
    neo4j_uri = os.environ.get("NEO4J_URI")
    neo4j_user = os.environ.get("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.environ.get("NEO4J_PASSWORD")
    azure_endpoint = os.environ.get("AZURE_AI_SERVICES_ENDPOINT")
    embedding_model = os.environ.get("AZURE_AI_EMBEDDING_NAME", "text-embedding-3-small")

    if not neo4j_uri or not neo4j_password:
        print("Error: NEO4J_URI and NEO4J_PASSWORD must be set in .env")
        sys.exit(1)
    if not azure_endpoint:
        print("Error: AZURE_AI_SERVICES_ENDPOINT must be set in .env")
        sys.exit(1)

    # --- Connect to Azure OpenAI ---
    print("Connecting to Azure OpenAI...")
    credential = DefaultAzureCredential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default")
    openai_client = AzureOpenAI(
        azure_endpoint=azure_endpoint,
        azure_ad_token=token.token,
        api_version="2024-06-01",
    )

    # --- Generate embeddings ---
    print(f"Generating embeddings for {len(CHUNKS)} chunks...")
    chunk_texts = [c["text"] for c in CHUNKS]
    embeddings = get_embeddings(openai_client, chunk_texts, model=embedding_model)
    print(f"  Embedding dimension: {len(embeddings[0])}")

    # --- Connect to Neo4j ---
    print(f"Connecting to Neo4j at {neo4j_uri}...")
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    driver.verify_connectivity()

    with driver.session() as session:
        # Clear existing data (with confirmation)
        result = session.run("MATCH (n) RETURN count(n) AS cnt")
        node_count = result.single()["cnt"]
        if node_count > 0:
            print(f"WARNING: This will delete all {node_count} nodes in {neo4j_uri}")
            if "--yes" not in sys.argv:
                answer = input("Continue? [y/N] ")
                if answer.lower() != "y":
                    print("Aborted.")
                    driver.close()
                    sys.exit(0)
        print("Clearing existing data...")
        session.run("MATCH (n) DETACH DELETE n")

        # Drop existing indexes (ignore errors)
        for idx in ["chunkEmbeddings", "search_chunks"]:
            try:
                session.run(f"DROP INDEX {idx}")
            except Exception:
                pass

        # Create companies
        print("Creating companies...")
        for company in COMPANIES:
            session.run(
                "CREATE (c:Company {name: $name, ticker: $ticker})",
                name=company["name"],
                ticker=company["ticker"],
            )

        # Create documents and link to companies
        print("Creating documents...")
        for doc in DOCUMENTS:
            session.run(
                """
                MATCH (c:Company {name: $company})
                CREATE (d:Document {title: $title})
                CREATE (c)-[:FILED]->(d)
                """,
                title=doc["title"],
                company=doc["company"],
            )

        # Create risk factors
        print("Creating risk factors...")
        for company, risks in RISK_FACTORS.items():
            for risk in risks:
                session.run(
                    """
                    MATCH (c:Company {name: $company})
                    CREATE (r:RiskFactor {name: $name, description: $desc})
                    CREATE (c)-[:FACES_RISK]->(r)
                    """,
                    company=company,
                    name=risk["name"],
                    desc=risk["description"],
                )

        # Create products
        print("Creating products...")
        for company, products in PRODUCTS.items():
            for prod in products:
                session.run(
                    """
                    MATCH (c:Company {name: $company})
                    CREATE (p:Product {name: $prod})
                    CREATE (c)-[:MENTIONS]->(p)
                    """,
                    company=company,
                    prod=prod,
                )

        # Create chunks with embeddings
        print("Creating chunks with embeddings...")
        for i, chunk in enumerate(CHUNKS):
            session.run(
                """
                MATCH (d:Document {title: $doc})
                CREATE (ch:Chunk {text: $text, embedding: $embedding})
                CREATE (ch)-[:FROM_DOCUMENT]->(d)
                """,
                doc=chunk["doc"],
                text=chunk["text"],
                embedding=embeddings[i],
            )

        # Create indexes
        print("Creating fulltext index 'search_chunks'...")
        session.run(
            "CREATE FULLTEXT INDEX search_chunks IF NOT EXISTS "
            "FOR (c:Chunk) ON EACH [c.text]"
        )

        print("Creating vector index 'chunkEmbeddings'...")
        session.run(
            "CREATE VECTOR INDEX chunkEmbeddings IF NOT EXISTS "
            "FOR (c:Chunk) ON c.embedding "
            "OPTIONS {indexConfig: {`vector.dimensions`: $dim, `vector.similarity_function`: 'cosine'}}",
            dim=len(embeddings[0]),
        )

        # Wait for indexes to come online
        print("Waiting for indexes to come online...")
        for _ in range(30):
            result = session.run(
                "SHOW INDEXES YIELD name, state "
                "WHERE name IN ['chunkEmbeddings', 'search_chunks'] "
                "RETURN name, state"
            )
            states = {r["name"]: r["state"] for r in result}
            if all(s == "ONLINE" for s in states.values()) and len(states) == 2:
                break
            time.sleep(2)

        # Verify
        result = session.run("MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt ORDER BY cnt DESC")
        print("\nData loaded:")
        for r in result:
            print(f"  {r['label']:15s} {r['cnt']}")

        result = session.run("SHOW INDEXES YIELD name, type, state WHERE name IN ['chunkEmbeddings', 'search_chunks'] RETURN name, type, state")
        print("\nIndexes:")
        for r in result:
            print(f"  {r['name']:20s} {r['type']:10s} {r['state']}")

    driver.close()
    print("\nDone! Database is ready for samples.")


if __name__ == "__main__":
    main()
