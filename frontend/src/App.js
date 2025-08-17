import React, { useEffect, useState } from "react";
import "./App.css";

export default function App() {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [filters, setFilters] = useState({
    language: "",
    sentiment: "",
    bias: ""
  });
  const [ingesting, setIngesting] = useState(false);
  const [ingestStatus, setIngestStatus] = useState(null);

  // Fetch articles from backend
  const fetchArticles = async (query = "", currentFilters = filters) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (query) params.append('q', query);
      if (currentFilters.language) params.append('language', currentFilters.language);
      if (currentFilters.sentiment) params.append('sentiment', currentFilters.sentiment);
      if (currentFilters.bias) params.append('bias', currentFilters.bias);
      params.append('size', '20');

      console.log('DEBUG - Fetching with params:', params.toString());
      
      const response = await fetch(`http://localhost:8000/articles/search?${params}`);
      const data = await response.json();
      
      console.log('DEBUG - API Response:', data);
      
      // Debug: Log the first article to see what fields we're getting
      if (data.results && data.results.length > 0) {
        console.log("DEBUG - First article from API:", data.results[0]);
        console.log("DEBUG - First article fields:", Object.keys(data.results[0]));
        console.log("DEBUG - Has summary:", !!data.results[0].summary, "Value:", data.results[0].summary);
        console.log("DEBUG - Has sentiment:", !!data.results[0].sentiment_overall, "Value:", data.results[0].sentiment_overall);
        console.log("DEBUG - Has bias:", !!data.results[0].bias_overall, "Value:", data.results[0].bias_overall);
        console.log("DEBUG - Sentiment score:", data.results[0].sentiment_score);
        console.log("DEBUG - Bias score:", data.results[0].bias_score);
      } else {
        console.log("DEBUG - No articles in response");
      }
      
      setArticles(data.results || []);
    } catch (error) {
      console.error('Error fetching articles:', error);
      setArticles([]);
    }
    setLoading(false);
  };

  // Ingest new articles
  const ingestArticles = async () => {
    setIngesting(true);
    setIngestStatus(null);
    try {
      console.log('DEBUG - Starting ingestion...');
      const response = await fetch('http://localhost:8000/ingest/run?limit_per_feed=20', {
        method: 'POST'
      });
      const data = await response.json();
      console.log('DEBUG - Ingestion response:', data);
      setIngestStatus(data);
      
      if (!data.error) {
        console.log('DEBUG - Ingestion successful, fetching articles...');
        await fetchArticles(searchQuery, filters);
      }
    } catch (error) {
      console.error('Error ingesting articles:', error);
      setIngestStatus({ error: 'Failed to ingest articles' });
    }
    setIngesting(false);
  };

  // Handle search
  const handleSearch = () => {
    console.log('DEBUG - Searching with query:', searchQuery, 'filters:', filters);
    fetchArticles(searchQuery, filters);
  };

  // Handle filter changes
  const handleFilterChange = (filterType, value) => {
    const newFilters = { ...filters, [filterType]: value };
    console.log('DEBUG - Filter changed:', filterType, '=', value, 'All filters:', newFilters);
    setFilters(newFilters);
    fetchArticles(searchQuery, newFilters);
  };

  // Load articles on component mount
  useEffect(() => {
    console.log('DEBUG - Component mounted, fetching initial articles...');
    fetchArticles();
  }, []);

  if (loading) {
    return (
      <div className="loading">
        <p>Loading articles...</p>
      </div>
    );
  }

  return (
    <div className="container">
      <header className="header">
        <h1>News Analyzer</h1>
        <button 
          onClick={ingestArticles} 
          disabled={ingesting}
          className={`ingest-btn ${ingesting ? 'loading' : ''}`}
        >
          {ingesting ? 'Ingesting...' : 'Ingest New Articles'}
        </button>
      </header>

      {/* Ingest Status */}
      {ingestStatus && (
        <div className={`status ${ingestStatus.error ? 'error' : 'success'}`}>
          {ingestStatus.error || `Successfully ingested ${ingestStatus.indexed} articles`}
        </div>
      )}

      {/* Search and Filters */}
      <div className="search-section">
        <div className="search-bar">
          <input
            type="text"
            placeholder="Search articles..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          />
          <button onClick={handleSearch}>Search</button>
        </div>

        <div className="filters">
          <select 
            value={filters.language} 
            onChange={(e) => handleFilterChange('language', e.target.value)}
          >
            <option value="">All Languages</option>
            <option value="en">English</option>
            <option value="hi">Hindi</option>
          </select>

          <select 
            value={filters.sentiment} 
            onChange={(e) => handleFilterChange('sentiment', e.target.value)}
          >
            <option value="">All Sentiments</option>
            <option value="positive">Positive</option>
            <option value="neutral">Neutral</option>
            <option value="negative">Negative</option>
          </select>

          <select 
            value={filters.bias} 
            onChange={(e) => handleFilterChange('bias', e.target.value)}
          >
            <option value="">All Bias Types</option>
            <option value="neutral">Neutral</option>
            <option value="left-leaning">Left-leaning</option>
            <option value="right-leaning">Right-leaning</option>
            <option value="pro-government">Pro-government</option>
            <option value="anti-government">Anti-government</option>
          </select>
        </div>
      </div>

      {/* Debug Info */}
      <div style={{ background: '#f0f0f0', padding: '10px', margin: '10px 0', fontSize: '12px' }}>
        <strong>DEBUG INFO:</strong> Found {articles.length} articles
        {articles.length > 0 && (
          <div>
            First article has: 
            summary={!!articles[0]?.summary ? 'YES' : 'NO'}, 
            sentiment={articles[0]?.sentiment_overall || 'MISSING'}, 
            bias={articles[0]?.bias_overall || 'MISSING'}
          </div>
        )}
      </div>

      {/* Articles */}
      {articles.length === 0 ? (
        <div className="no-articles">
          <p>No articles found. Try adjusting your search or ingest new articles.</p>
        </div>
      ) : (
        <div className="articles-grid">
          {articles.map((article, idx) => {
            console.log(`DEBUG - Rendering article ${idx}:`, {
              title: article.title,
              hasSummary: !!article.summary,
              sentiment: article.sentiment_overall,
              bias: article.bias_overall
            });
            
            return (
              <div key={idx} className="article-card">
                <div className="article-header">
                  <h2>{article.title || 'Untitled'}</h2>
                  <a href={article.url} target="_blank" rel="noopener noreferrer" className="external-link">
                    🔗
                  </a>
                </div>
                
                <div className="article-meta">
                  <span className="source">{article.source_name || 'Unknown Source'}</span>
                  {article.published_date && (
                    <span className="date">
                      {new Date(article.published_date).toLocaleDateString()}
                    </span>
                  )}
                </div>

                {/* Debug info for each article */}
                <div style={{ fontSize: '10px', color: '#666', marginBottom: '10px' }}>
                  DEBUG: sentiment={article.sentiment_overall || 'NONE'}, 
                  bias={article.bias_overall || 'NONE'}, 
                  summary={article.summary ? 'YES' : 'NO'}
                </div>

                <div className="analysis-badges">
                  <span className={`badge sentiment-${article.sentiment_overall || 'unknown'}`}>
                    Sentiment: {article.sentiment_overall || 'Unknown'} 
                    {article.sentiment_score && ` (${(article.sentiment_score * 100).toFixed(1)}%)`}
                  </span>
                  <span className={`badge bias-${(article.bias_overall || 'unknown').replace('-', '')}`}>
                    Bias: {article.bias_overall || 'Unknown'} 
                    {article.bias_score && ` (${(article.bias_score * 100).toFixed(1)}%)`}
                  </span>
                  <span className="badge language">
                    {(article.language || 'unknown').toUpperCase()}
                  </span>
                </div>

                {article.summary ? (
                  <div className="summary">
                    <strong>Summary:</strong>
                    <p>{article.summary}</p>
                  </div>
                ) : (
                  <div className="summary" style={{ color: '#999' }}>
                    <strong>Summary:</strong>
                    <p>No summary available</p>
                  </div>
                )}

                {article.entities && article.entities.length > 0 && (
                  <div className="entities">
                    <strong>Key Entities:</strong>
                    <div className="entity-tags">
                      {article.entities.slice(0, 6).map((entity, entityIdx) => (
                        <span key={entityIdx} className="entity-tag">
                          {entity.name} ({entity.type})
                        </span>
                      ))}
                      {article.entities.length > 6 && (
                        <span className="entity-tag more">
                          +{article.entities.length - 6} more
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}