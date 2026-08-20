import React, { useState, useEffect } from 'react';

function App() {
  const [stats, setStats] = useState({ users: 0, pro: 0, active_monitors: 0 });
  const [users, setUsers] = useState({});
  const [admins, setAdmins] = useState({});
  const [newAdminId, setNewAdminId] = useState('');
  const [newAdminName, setNewAdminName] = useState('');
  
  // Pravalar
  const availablePermissions = ['broadcast', 'manage_users', 'manage_admins', 'view_stats'];
  const [selectedPerms, setSelectedPerms] = useState([]);

  // Xabar yuborish
  const [broadcastText, setBroadcastText] = useState('');
  const [broadcastStatus, setBroadcastStatus] = useState('');

  useEffect(() => {
    fetchStats();
    fetchAdmins();
    fetchUsers();
  }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch('http://localhost:8080/api/stats');
      setStats(await res.json());
    } catch (e) { console.error(e); }
  };

  const fetchAdmins = async () => {
    try {
      const res = await fetch('http://localhost:8080/api/admins');
      setAdmins(await res.json());
    } catch (e) { console.error(e); }
  };

  const fetchUsers = async () => {
    try {
      const res = await fetch('http://localhost:8080/api/users');
      setUsers(await res.json());
    } catch (e) { console.error(e); }
  };

  const togglePro = async (id, currentPro) => {
    try {
      await fetch(`http://localhost:8080/api/users/${id}/pro`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_pro: !currentPro })
      });
      fetchUsers();
      fetchStats();
    } catch (e) { console.error(e); }
  };

  const sendBroadcast = async () => {
    if (!broadcastText.trim()) return;
    setBroadcastStatus('Yuborilmoqda...');
    try {
      const res = await fetch('http://localhost:8080/api/broadcast', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: broadcastText })
      });
      const data = await res.json();
      if(data.success) {
        setBroadcastStatus(`Muvaffaqiyatli! ${data.count} kishiga yuborildi.`);
        setBroadcastText('');
      } else {
        setBroadcastStatus('Xatolik yuz berdi!');
      }
    } catch (e) { 
      console.error(e); 
      setBroadcastStatus('Xatolik yuz berdi!');
    }
  };

  const addAdmin = async () => {
    if (!newAdminId) return;
    try {
      await fetch('http://localhost:8080/api/admins', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ admin_id: newAdminId, name: newAdminName, permissions: selectedPerms })
      });
      setNewAdminId('');
      setNewAdminName('');
      setSelectedPerms([]);
      fetchAdmins();
    } catch (e) { console.error(e); }
  };

  const removeAdmin = async (id) => {
    try {
      await fetch(`http://localhost:8080/api/admins/${id}`, { method: 'DELETE' });
      fetchAdmins();
    } catch (e) { console.error(e); }
  };

  const togglePerm = (perm) => {
    if (selectedPerms.includes(perm)) setSelectedPerms(selectedPerms.filter(p => p !== perm));
    else setSelectedPerms([...selectedPerms, perm]);
  };

  const loadForEdit = (id, data) => {
    setNewAdminId(id);
    setNewAdminName(data.name || '');
    setSelectedPerms(data.permissions || []);
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-4xl font-bold mb-8 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-500">
          TradingView Bot Admin Panel
        </h1>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 shadow-lg">
            <h2 className="text-xl text-gray-400 mb-2">Foydalanuvchilar</h2>
            <p className="text-4xl font-bold">{stats.users}</p>
          </div>
          <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 shadow-lg">
            <h2 className="text-xl text-gray-400 mb-2">PRO A'zolar</h2>
            <p className="text-4xl font-bold">{stats.pro}</p>
          </div>
          <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 shadow-lg">
            <h2 className="text-xl text-gray-400 mb-2">Faol Monitoringlar</h2>
            <p className="text-4xl font-bold">{stats.active_monitors}</p>
          </div>
        </div>

        <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 shadow-lg mb-8">
          <h2 className="text-2xl font-bold mb-4 border-b border-gray-700 pb-2">📢 Ommaviy Xabar Yuborish</h2>
          <textarea 
            rows="4" 
            placeholder="Xabar matnini kiriting (HTML teglar ishlatsangiz bo'ladi)..." 
            className="w-full bg-gray-700 p-3 rounded text-white focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
            value={broadcastText}
            onChange={e => setBroadcastText(e.target.value)}
          ></textarea>
          <div className="flex items-center gap-4">
            <button onClick={sendBroadcast} className="bg-green-600 hover:bg-green-500 px-6 py-2 rounded font-bold transition">
              Barchaga Yuborish
            </button>
            <span className="text-sm text-gray-300">{broadcastStatus}</span>
          </div>
        </div>

        <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 shadow-lg mb-8">
          <h2 className="text-2xl font-bold mb-4 border-b border-gray-700 pb-2">👥 Foydalanuvchilar Boshqaruvi</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-700">
                  <th className="p-3">ID</th>
                  <th className="p-3">Til</th>
                  <th className="p-3">Kuzatuvlar (Monitoring)</th>
                  <th className="p-3">PRO Status</th>
                  <th className="p-3">Harakatlar</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(users).map(([id, data]) => (
                  <tr key={id} className="border-b border-gray-700 hover:bg-gray-750">
                    <td className="p-3">{id}</td>
                    <td className="p-3">{data.lang?.toUpperCase() || 'UZ'}</td>
                    <td className="p-3">{Object.keys(data.monitoring || {}).length} ta</td>
                    <td className="p-3">
                      {data.is_pro ? (
                        <span className="bg-yellow-500/20 text-yellow-500 px-2 py-1 rounded text-xs font-bold">PRO</span>
                      ) : (
                        <span className="bg-gray-600 px-2 py-1 rounded text-xs">Oddiy</span>
                      )}
                    </td>
                    <td className="p-3">
                      <button 
                        onClick={() => togglePro(id, data.is_pro)}
                        className={`px-3 py-1 rounded text-sm font-bold transition ${data.is_pro ? 'bg-red-600 hover:bg-red-500' : 'bg-blue-600 hover:bg-blue-500'}`}
                      >
                        {data.is_pro ? "PRO ni olish" : "PRO berish"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {Object.keys(users).length === 0 && <p className="text-gray-400 mt-4 text-center">Foydalanuvchilar yo'q.</p>}
          </div>
        </div>

        <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 shadow-lg mb-8">
          <h2 className="text-2xl font-bold mb-4 border-b border-gray-700 pb-2">Admin Boshqaruvi (Qo'shish / Tahrirlash)</h2>
          <div className="flex flex-col md:flex-row gap-4 mb-4">
            <input 
              type="text" placeholder="Telegram ID (masalan: 8357557157)" 
              className="bg-gray-700 p-3 rounded text-white flex-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={newAdminId} onChange={e => setNewAdminId(e.target.value)}
            />
            <input 
              type="text" placeholder="Ismi" 
              className="bg-gray-700 p-3 rounded text-white flex-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={newAdminName} onChange={e => setNewAdminName(e.target.value)}
            />
          </div>
          
          <h3 className="text-lg mb-2 text-gray-300">Ruxsatlar (Pravalar):</h3>
          <div className="flex flex-wrap gap-3 mb-6">
            {availablePermissions.map(p => (
              <label key={p} className="flex items-center gap-2 bg-gray-700 px-4 py-2 rounded-lg cursor-pointer hover:bg-gray-600 transition">
                <input type="checkbox" checked={selectedPerms.includes(p)} onChange={() => togglePerm(p)} className="w-4 h-4 text-blue-500 rounded focus:ring-blue-500" />
                <span className="capitalize">{p.replace('_', ' ')}</span>
              </label>
            ))}
          </div>
          
          <button onClick={addAdmin} className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 px-8 py-3 rounded-lg font-bold shadow-lg transition">
            Saqlash
          </button>
        </div>

        <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 shadow-lg">
          <h2 className="text-2xl font-bold mb-4 border-b border-gray-700 pb-2">Boshqa Adminlar</h2>
          {Object.keys(admins).length === 0 ? (
            <p className="text-gray-400">Hech qanday qo'shimcha admin topilmadi.</p>
          ) : (
            <div className="space-y-4">
              {Object.entries(admins).map(([id, data]) => (
                <div key={id} className="bg-gray-700 p-5 rounded-lg flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                  <div>
                    <h3 className="text-xl font-bold">{data.name} <span className="text-sm font-normal text-gray-400 ml-2">ID: {id}</span></h3>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {data.permissions && data.permissions.map(p => (
                        <span key={p} className="bg-gray-800 border border-gray-600 text-xs px-3 py-1 rounded-full text-blue-400">
                          {p.replace('_', ' ')}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="flex gap-2 w-full md:w-auto">
                    <button onClick={() => loadForEdit(id, data)} className="flex-1 md:flex-none bg-gray-600 hover:bg-gray-500 px-4 py-2 rounded font-bold transition">
                      Tahrirlash
                    </button>
                    <button onClick={() => removeAdmin(id)} className="flex-1 md:flex-none bg-red-600 hover:bg-red-500 px-4 py-2 rounded font-bold transition">
                      O'chirish
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
