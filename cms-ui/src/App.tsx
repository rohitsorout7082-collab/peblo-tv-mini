import React, { useEffect, useState } from 'react';
import axios from 'axios';

interface Episode {
  id: string;
  title: string;
  content_group: string;
  language: string;
  duration_seconds?: number;
}

interface Season {
  id: string;
  season_number: number;
  episodes: Episode[];
}

interface Show {
  id: string;
  title: string;
  synopsis: string;
  section: string;
  category: string;
  status: string;
  seasons: Season[];
}

interface ValidationIssue {
  level: string;
  entity: string;
  id: string;
  message: string;
}

interface ValidationReport {
  can_publish: boolean;
  total_errors: number;
  total_warnings: number;
  issues: ValidationIssue[];
}

const API_BASE = "http://127.0.0.1:8000/api";

export default function App() {
  const [shows, setShows] = useState<Show[]>([]);
  const [report, setReport] = useState<ValidationReport | null>(null);
  const [editingShow, setEditingShow] = useState<Show | null>(null);
  const [publishMessage, setPublishMessage] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'cms' | 'viewer'>('cms');

  const fetchData = async () => {
    try {
      const [showsRes, reportRes] = await Promise.all([
        axios.get(`${API_BASE}/shows`),
        axios.get(`${API_BASE}/validate`)
      ]);
      setShows(showsRes.data);
      setReport(reportRes.data);
    } catch (err) {
      console.error("Failed to load CMS data", err);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleUpdateShow = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingShow) return;
    try {
      await axios.put(`${API_BASE}/shows/${editingShow.id}`, {
        title: editingShow.title,
        synopsis: editingShow.synopsis,
        section: editingShow.section,
        category: editingShow.category
      });
      setEditingShow(null);
      fetchData();
    } catch (err) {
      alert("Failed to update show");
    }
  };

  const handleFixDuplicate = async (episodeId: string) => {
    const fixedKey = `motis-many-lives-s01e02-v2-${Date.now().toString().slice(-4)}`;
    try {
      await axios.post(`${API_BASE}/episodes/${episodeId}/resolve?new_content_group=${fixedKey}`);
      fetchData();
    } catch (err) {
      alert("Failed to resolve duplicate");
    }
  };

  const handleUploadPoster = async (showId: string, file: File) => {
    setUploadError(null);
    const formData = new FormData();
    formData.append("parent_type", "show");
    formData.append("parent_id", showId);
    formData.append("slot_type", "poster");
    formData.append("file", file);

    try {
      await axios.post(`${API_BASE}/artworks/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      alert("Poster uploaded successfully!");
      fetchData();
    } catch (err: any) {
      setUploadError(err.response?.data?.detail || "Upload rejected: Aspect ratio must be 2:3 and size <= 200KB.");
    }
  };

  const handlePublish = async () => {
    try {
      const res = await axios.post(`${API_BASE}/publish`);
      setPublishMessage(res.data.message);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail?.message || "Publish blocked by validation rules!");
    }
  };

  const displayedShows = viewMode === 'viewer'
    ? shows.filter(s => s.status.toLowerCase() === 'published')
    : shows;

  return (
    <div className="container">
      {/* Header with Navigation Switch */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0 }}>Peblo TV Mini — {viewMode === 'cms' ? 'CMS Dashboard' : 'Live Viewer Catalog'}</h1>
          <p style={{ color: '#94a3b8', margin: 0 }}>FastAPI + React CMS & Atomic Publishing Pipeline</p>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <button 
            className="btn" 
            style={{ background: viewMode === 'cms' ? '#2563eb' : '#334155' }}
            onClick={() => setViewMode('cms')}
          >
            CMS Admin View
          </button>
          <button 
            className="btn" 
            style={{ background: viewMode === 'viewer' ? '#10b981' : '#334155' }}
            onClick={() => setViewMode('viewer')}
          >
            Live Viewer Experience
          </button>
          {viewMode === 'cms' && (
            <button 
              className="btn btn-publish" 
              disabled={!report?.can_publish} 
              onClick={handlePublish}
            >
              {report?.can_publish ? "Publish to Viewer App" : "Publish Blocked"}
            </button>
          )}
        </div>
      </header>

      {/* Status Messages */}
      {publishMessage && (
        <div className="card" style={{ borderLeft: '4px solid #10b981' }}>
          <strong>Success:</strong> {publishMessage}
        </div>
      )}

      {uploadError && (
        <div className="card" style={{ borderLeft: '4px solid #ef4444', color: '#f87171' }}>
          <strong>Upload Error:</strong> {uploadError}
        </div>
      )}

      {/* Validation Banner (Only visible in CMS Mode) */}
      {viewMode === 'cms' && report && (
        <div className="card" style={{ borderLeft: `4px solid ${report.can_publish ? '#10b981' : '#ef4444'}` }}>
          <h3>Validation Status: {report.can_publish ? "Ready to Publish" : "Action Required"}</h3>
          <p>
            Errors: <span className="badge badge-error">{report.total_errors}</span> | 
            Warnings: <span className="badge badge-warning">{report.total_warnings}</span>
          </p>
          <ul style={{ paddingLeft: 20 }}>
            {report.issues.map((issue, idx) => (
              <li key={idx} style={{ marginBottom: 8, color: issue.level === 'error' ? '#f87171' : '#f59e0b' }}>
                <strong>[{issue.level.toUpperCase()}]</strong> {issue.message}
                {issue.entity === 'episode' && (
                  <button 
                    className="btn" 
                    style={{ marginLeft: 12, padding: '2px 8px', fontSize: 11, background: '#10b981' }}
                    onClick={() => handleFixDuplicate(issue.id)}
                  >
                    Auto-Fix Key
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Shows Grid */}
      <h2>{viewMode === 'cms' ? `All Shows (${displayedShows.length})` : `Published Shows Catalog (${displayedShows.length})`}</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 16 }}>
        {displayedShows.map(show => (
          <div key={show.id} className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className={`badge badge-${show.status.toLowerCase()}`}>{show.status}</span>
              {viewMode === 'cms' && (
                <button className="btn" style={{ padding: '2px 8px', fontSize: 12 }} onClick={() => setEditingShow(show)}>Edit</button>
              )}
            </div>
            <h3 style={{ margin: '12px 0 6px 0' }}>{show.title}</h3>
            <p style={{ color: '#94a3b8', fontSize: 13, height: 38, overflow: 'hidden' }}>{show.synopsis || "No synopsis available."}</p>
            
            <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 12 }}>
              <div><strong>Category:</strong> {show.category || "Unassigned"}</div>
              <div><strong>Seasons:</strong> {show.seasons.length}</div>
              <div><strong>Episodes:</strong> {show.seasons.reduce((sum, s) => sum + s.episodes.length, 0)}</div>
            </div>

            {viewMode === 'cms' && (
              <div style={{ borderTop: '1px solid #334155', paddingTop: 10 }}>
                <label style={{ fontSize: 11, color: '#cbd5e1' }}>Upload Poster (2:3, &lt;200KB):</label>
                <input 
                  type="file" 
                  accept="image/*"
                  style={{ fontSize: 11, marginTop: 4 }} 
                  onChange={(e) => {
                    if (e.target.files?.[0]) handleUploadPoster(show.id, e.target.files[0]);
                  }} 
                />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Edit Modal */}
      {editingShow && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div className="card" style={{ width: 450, background: '#1e293b' }}>
            <h3>Edit Show Details</h3>
            <form onSubmit={handleUpdateShow}>
              <label>Title</label>
              <input 
                className="input-field" 
                value={editingShow.title} 
                onChange={e => setEditingShow({ ...editingShow, title: e.target.value })} 
                required 
              />
              <label>Category (e.g. Animation, Rhymes, Kids)</label>
              <input 
                className="input-field" 
                value={editingShow.category || ''} 
                onChange={e => setEditingShow({ ...editingShow, category: e.target.value })} 
              />
              <label>Synopsis</label>
              <textarea 
                className="input-field" 
                rows={3} 
                value={editingShow.synopsis || ''} 
                onChange={e => setEditingShow({ ...editingShow, synopsis: e.target.value })} 
              />
              <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                <button type="button" className="btn" style={{ background: '#64748b' }} onClick={() => setEditingShow(null)}>Cancel</button>
                <button type="submit" className="btn">Save Changes</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}