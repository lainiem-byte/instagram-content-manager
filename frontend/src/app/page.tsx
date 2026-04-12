'use client';

import { useState, useEffect } from 'react';

// Icons (Simple SVGs for minimal dependency)
const DashboardIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>
);

const HistoryIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/></svg>
);

const PostIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg>
);

const UserIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
);

const RefreshIcon = ({ className }: { className?: string }) => (
  <svg 
    xmlns="http://www.w3.org/2000/svg" 
    width="16" 
    height="16" 
    viewBox="0 0 24 24" 
    fill="none" 
    stroke="currentColor" 
    strokeWidth="2" 
    strokeLinecap="round" 
    strokeLinejoin="round"
    className={className}
  >
    <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>
  </svg>
);

const CheckIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-emerald-400"><path d="M20 6 9 17l-5-5"/></svg>
);

const WarningIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-amber-400"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>
);

export default function Dashboard() {
  const [profiles, setProfiles] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [status, setStatus] = useState<any>(null);
  const [queue, setQueue] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [activeProfile, setActiveProfile] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'dashboard' | 'profiles' | 'activity' | 'gallery'>('dashboard');
  const [backendHealth, setBackendHealth] = useState<'IDLE' | 'CONNECTED' | 'ERROR'>('IDLE');

  // Dynamic API base: use the same hostname as the frontend
  // Initialized at empty to prevent pre-mature fetch attempts to localhost on production domains
  const [apiBase, setApiBase] = useState('');

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const hostname = window.location.hostname;
      const protocol = window.location.protocol;
      
      // PRODUCTION (VPS with Nginx Proxy): Use relative path to avoid CORS/Mixed Content
      // LOCAL: Fallback to direct localhost:8000
      if (hostname === 'localhost' || hostname === '127.0.0.1') {
          setApiBase('http://localhost:8000/api');
      } else {
          // This assumes Nginx proxies /api to port 8000
          setApiBase('/api');
      }
    }
  }, []);

  const fetchData = async () => {
    if (!apiBase) return;
    setFetching(true);
    try {
      const profRes = await fetch(`${apiBase}/profiles`);
      if (!profRes.ok) throw new Error('API Unreachable');
      
      const profData = await profRes.json();
      setProfiles(profData);
      setBackendHealth('CONNECTED');
      
      if (profData.length > 0 && !activeProfile) {
        setActiveProfile(profData[0].account_id);
        await loadProfileData(profData[0].account_id);
      } else if (activeProfile) {
        await loadProfileData(activeProfile);
      }
    } catch (err) {
      console.error('Error fetching data:', err);
      setBackendHealth('ERROR');
    } finally {
      setFetching(false);
    }
  };

  const loadProfileData = async (profileId: string) => {
    try {
      const [histRes, statRes, queueRes] = await Promise.all([
        fetch(`${apiBase}/history`),
        fetch(`${apiBase}/status/${profileId}`),
        fetch(`${apiBase}/queue/${profileId}`)
      ]);

      setHistory(await histRes.json());
      setStatus(await statRes.json());
      setQueue(await queueRes.json());
    } catch (err) {
      console.error('Error loading profile data:', err);
    }
  };

  useEffect(() => {
    if (apiBase) {
      fetchData();
      const interval = setInterval(fetchData, 30000); // refresh every 30s
      return () => clearInterval(interval);
    }
  }, [activeProfile, apiBase]);

  const handleProfileChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    setActiveProfile(val);
    loadProfileData(val);
  };

  const run_pipeline = async () => {
    console.log("Button clicked. Active Profile:", activeProfile);
    
    if (!activeProfile) {
      alert('⚠️ Manual selection required: Please pick a profile from the dropdown.');
      return;
    }

    setLoading(true);
    try {
      const url = `${apiBase}/run/${activeProfile}`;
      console.log("Sending POST to:", url);
      
      const res = await fetch(url, { 
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });

      if (res.ok) {
        alert('🚀 Pipeline started in background!');
        setTimeout(fetchData, 2000);
      } else {
        const errorText = await res.text();
        console.error("Server error response:", errorText);
        alert(`❌ Server error (${res.status}): ${errorText}`);
      }
    } catch (err: any) {
      console.error("Network or Fetch error:", err);
      alert(`❌ CONNECTION FAILED: Check code console. Error: ${err.message}`);
    } finally {
      setLoading(true); // Keep it loading for a moment to prevent double-clicks
      setTimeout(() => setLoading(false), 5000);
    }
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'profiles':
        return (
          <div className="space-y-6 animate-in fade-in duration-500">
            <h2 className="text-2xl font-bold mb-6">Brand Profiles</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {profiles.map((p, i) => (
                <div key={i} className="glass rounded-2xl p-6 border border-slate-700/50">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-xl font-bold text-blue-400">{p.brand_name}</h3>
                      <p className="opacity-60">{p.instagram_handle}</p>
                    </div>
                    <span className={`px-2 py-1 rounded text-[10px] font-bold ${p.active ? 'bg-emerald-500/10 text-emerald-400' : 'bg-slate-500/10 text-slate-400'}`}>
                      {p.active ? 'ACTIVE' : 'INACTIVE'}
                    </span>
                  </div>
                  <div className="space-y-2 text-sm">
                    {p.overview && <p><span className="opacity-40">Overview:</span> <span className="text-xs leading-relaxed italic">{p.overview}</span></p>}
                    <p><span className="opacity-40">Voice:</span> {p.brand_voice}</p>
                    <p><span className="opacity-40">Aesthetic:</span> {p.aesthetic}</p>
                    <p><span className="opacity-40">Hashtags:</span> {p.branded_hashtags?.join(', ')}</p>
                    {p.fonts && p.fonts.length > 0 && <p><span className="opacity-40">Fonts:</span> {p.fonts.join(', ')}</p>}
                    <p><span className="opacity-40">Website:</span> <a href={p.post_link} target="_blank" className="text-blue-400 hover:underline">{p.post_link}</a></p>
                    <p><span className="opacity-40">Folder ID:</span> <code className="text-xs">{p.drive_folder_id}</code></p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      case 'activity':
        return (
          <div className="animate-in fade-in duration-500">
            <h2 className="text-2xl font-bold mb-6">Full Activity Log</h2>
            <div className="glass rounded-2xl overflow-hidden">
               <table className="w-full text-left border-collapse">
                 <thead>
                   <tr className="bg-slate-900/50 border-b border-slate-800">
                     <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider opacity-60">Status</th>
                     <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider opacity-60">Type</th>
                     <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider opacity-60">Timestamp</th>
                     <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider opacity-60">Post ID</th>
                   </tr>
                 </thead>
                 <tbody>
                   {history.map((h, i) => (
                     <tr key={i} className="border-b border-slate-800 hover:bg-white/5 transition-colors">
                       <td className="px-6 py-4">
                         <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase ${h.status === 'Success' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'}`}>
                           {h.status}
                         </span>
                       </td>
                       <td className="px-6 py-4 font-medium uppercase text-xs">{h.post_type || 'POST'}</td>
                       <td className="px-6 py-4 opacity-60 text-sm">{new Date(h.timestamp).toLocaleString()}</td>
                       <td className="px-6 py-4 opacity-60 text-xs font-mono">{h.post_id || '-'}</td>
                     </tr>
                   ))}
                   {history.length === 0 && (
                     <tr>
                        <td colSpan={4} className="px-6 py-10 text-center opacity-40">No activity recorded yet</td>
                     </tr>
                   )}
                 </tbody>
               </table>
            </div>
          </div>
        );
      case 'gallery':
        return (
          <div className="animate-in fade-in duration-500">
            <h2 className="text-2xl font-bold mb-6">Drive Media Gallery</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-6">
              {queue.map((f, i) => (
                <div key={i} className="glass rounded-2xl p-4 flex flex-col group hover:border-blue-500/50 transition-all">
                  <div className="aspect-square bg-slate-900 rounded-xl overflow-hidden mb-3 relative flex items-center justify-center">
                     {f.id ? (
                        <img 
                          src={`https://lh3.googleusercontent.com/d/${f.id}`} 
                          alt={f.name} 
                          className="w-full h-full object-cover"
                        />
                     ) : <PostIcon />}
                     <div className="absolute bottom-2 left-2 bg-black/60 backdrop-blur-md px-2 py-1 rounded text-[10px] font-bold">
                       {f.mimeType?.split('/')[1]?.toUpperCase()}
                     </div>
                  </div>
                  <p className="text-sm font-medium truncate">{f.name}</p>
                </div>
              ))}
              {queue.length === 0 && (
                <div className="col-span-full py-20 glass rounded-2xl flex flex-col items-center justify-center opacity-40 border-dashed border-2">
                   <PostIcon />
                   <p className="mt-2 text-lg">Your gallery is currently empty</p>
                </div>
              )}
            </div>
          </div>
        );
      default:
        return (
          <>
            {/* Status Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
              <StatusCard 
                title="Feed Post" 
                status={status?.needs_main ? 'Pending' : 'Completed'} 
                icon={status?.needs_main ? <WarningIcon /> : <CheckIcon />}
                desc={status?.needs_main ? "Required for today's quota" : "Quota reached for today"}
              />
              <StatusCard 
                title="Story Post" 
                status={status?.needs_story ? 'Pending' : 'Completed'} 
                icon={status?.needs_story ? <WarningIcon /> : <CheckIcon />}
                desc={status?.needs_story ? "Required for today's quota" : "Quota reached for today"}
              />
              <StatusCard 
                title="Drive Sync" 
                status={queue.length > 0 ? 'Active' : 'Idle'} 
                icon={<RefreshIcon />}
                desc={`${queue.length} unprocessed media files in queue`}
              />
            </div>

            {/* Media Queue Preview */}
            <div className="mb-10">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold flex items-center gap-2">
                  <PostIcon /> Google Drive Queue
                </h2>
                <button 
                  onClick={() => setActiveTab('gallery')}
                  className="text-sm text-blue-400 hover:text-blue-300 font-medium"
                >
                  View All Gallery
                </button>
              </div>
              <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-hide">
                {queue.length > 0 ? queue.slice(0, 6).map((f, i) => (
                  <div key={i} className="min-w-[200px] h-[260px] glass rounded-2xl p-3 flex flex-col group cursor-pointer hover:border-blue-500/50 transition-all">
                    <div className="flex-1 bg-slate-900 rounded-xl overflow-hidden mb-3 relative flex items-center justify-center">
                       {f.id ? (
                          <img 
                            src={`https://lh3.googleusercontent.com/d/${f.id}`} 
                            alt={f.name} 
                            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                          />
                       ) : <PostIcon />}
                       <div className="absolute bottom-2 left-2 bg-black/60 backdrop-blur-md px-2 py-1 rounded text-[10px] uppercase font-bold tracking-wider">
                         {f.mimeType?.split('/')[1] || 'IMAGE'}
                       </div>
                    </div>
                    <p className="text-sm font-medium truncate mb-1">{f.name}</p>
                    <p className="text-[10px] opacity-40">{new Date(f.modifiedTime).toLocaleDateString()}</p>
                  </div>
                )) : (
                  <div className="w-full py-20 glass rounded-2xl flex flex-col items-center justify-center opacity-40 border-dashed border-2">
                     <PostIcon />
                     <p className="mt-2">No unprocessed media in folder</p>
                  </div>
                )}
              </div>
            </div>

            {/* Recent Activity Preview */}
            <div>
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold flex items-center gap-2">
                  <HistoryIcon /> Recent Activity
                </h2>
                <button 
                  onClick={() => setActiveTab('activity')}
                  className="text-sm text-blue-400 hover:text-blue-300 font-medium"
                >
                  Full Logs
                </button>
              </div>
              <div className="glass rounded-2xl overflow-hidden">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-900/50 border-b border-slate-800">
                      <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider opacity-60">Status</th>
                      <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider opacity-60">Type</th>
                      <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider opacity-60">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.slice(0, 5).map((h, i) => (
                      <tr key={i} className="border-b border-slate-800 hover:bg-white/5 transition-colors">
                        <td className="px-6 py-4">
                          <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase ${h.status === 'Success' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'}`}>
                            {h.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 font-medium uppercase text-xs">{h.post_type || 'POST'}</td>
                        <td className="px-6 py-4 opacity-60 text-sm">{new Date(h.timestamp).toLocaleString()}</td>
                      </tr>
                    ))}
                    {history.length === 0 && (
                      <tr>
                        <td colSpan={3} className="px-6 py-10 text-center opacity-40">No activity recorded yet</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        );
    }
  };

  return (
    <div className="flex min-h-screen bg-[#020617] text-slate-200">
      {/* Sidebar */}
      <aside className="w-64 glass border-r border-slate-800 p-6 flex flex-col fixed h-screen">
        <div 
          className="flex items-center gap-3 mb-10 cursor-pointer"
          onClick={() => setActiveTab('dashboard')}
        >
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center glow">
            <span className="font-bold text-lg">IG</span>
          </div>
          <span className="font-bold text-xl tracking-tight neon-text">Antigravity</span>
        </div>

        <nav className="flex-1 space-y-2">
          <NavItem 
            icon={<DashboardIcon />} 
            label="Dashboard" 
            active={activeTab === 'dashboard'} 
            onClick={() => setActiveTab('dashboard')} 
          />
          <NavItem 
            icon={<UserIcon />} 
            label="Profiles" 
            active={activeTab === 'profiles'} 
            onClick={() => setActiveTab('profiles')} 
          />
          <NavItem 
            icon={<HistoryIcon />} 
            label="Activity Log" 
            active={activeTab === 'activity'} 
            onClick={() => setActiveTab('activity')} 
          />
          <NavItem 
            icon={<PostIcon />} 
            label="Gallery" 
            active={activeTab === 'gallery'} 
            onClick={() => setActiveTab('gallery')} 
          />
        </nav>

        <div className="mt-auto pt-6 border-t border-slate-800 space-y-4">
          <button 
            onClick={() => window.open(`${apiBase.replace('/api', '')}/meta/login`, '_blank')}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold text-sm hover:from-blue-500 hover:to-indigo-500 transition-all shadow-lg shadow-blue-900/20"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/></svg>
            Connect Meta
          </button>

          <div className="p-4 rounded-xl bg-gradient-to-r from-slate-900 to-slate-800 border border-slate-700">
            <p className="text-sm font-medium opacity-70 mb-2">Backend Connection</p>
            <p className={`font-bold text-xs truncate ${profiles.length > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {profiles.length > 0 ? 'CONNECTED' : 'DISCONNECTED'}
            </p>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-8 overflow-y-auto ml-64">
        {/* Header */}
        <header className="flex justify-between items-center mb-10">
          <div>
            <h1 className="text-3xl font-bold mb-2 uppercase tracking-tight">
              {activeTab === 'dashboard' ? 'Social Dashboard' : activeTab}
            </h1>
            <p className="opacity-60">IG Content Management & Automation Ecosystem</p>
          </div>
          
          <div className="flex items-center gap-4">
             <select 
               value={activeProfile}
               onChange={handleProfileChange}
               className="bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none cursor-pointer"
             >
               {profiles.length === 0 && <option>Loading Profiles...</option>}
               {profiles.map(p => (
                 <option key={p.account_id} value={p.account_id}>{p.brand_name}</option>
               ))}
             </select>

             <button 
                onClick={run_pipeline} 
                disabled={loading}
                className={`px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-lg transition-colors flex items-center gap-2 ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {loading ? 'Processing...' : 'Run Pipeline Now'}
              </button>
             
             <button 
               onClick={fetchData} 
               title="Refresh Data" 
               disabled={fetching}
               className={`p-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-all flex items-center gap-2 ${fetching ? 'opacity-50' : ''}`}
             >
               <RefreshIcon className={fetching ? 'animate-spin' : ''} />
               {fetching && <span className="text-[10px] font-bold">SYCNING...</span>}
             </button>
          </div>
        </header>

        {renderContent()}
      </main>
    </div>
  );
}

function NavItem({ icon, label, active = false, onClick }: { icon: any, label: string, active?: boolean, onClick?: () => void }) {
  return (
    <div 
      onClick={onClick}
      className={`flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer transition-all ${active ? 'bg-blue-600/10 text-blue-400 border border-blue-600/20 glow' : 'hover:bg-white/5 opacity-60 hover:opacity-100'}`}
    >
      {icon}
      <span className="font-medium text-sm">{label}</span>
    </div>
  );
}

function StatusCard({ title, status, icon, desc }: { title: string, status: string, icon: any, desc: string }) {
  const isCompleted = status === 'Completed' || status === 'Active';
  
  return (
    <div className="glass rounded-2xl p-6 relative overflow-hidden group border border-slate-800 hover:border-slate-700 transition-colors">
      <div className={`absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-30 transition-opacity ${isCompleted ? 'text-blue-400' : 'text-amber-400'}`}>
        {icon}
      </div>
      <h3 className="text-sm font-medium opacity-60 mb-1 uppercase tracking-wider">{title}</h3>
      <div className="flex items-center gap-2 mb-2">
        <p className={`text-2xl font-bold ${isCompleted ? 'text-emerald-400' : (status === 'Pending' ? 'text-amber-400' : 'text-blue-400')}`}>{status}</p>
        <span className={status === 'Pending' ? 'animate-pulse' : ''}>{icon}</span>
      </div>
      <p className="text-xs opacity-40">{desc}</p>
    </div>
  );
}

