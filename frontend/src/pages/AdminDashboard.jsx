import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Box, Button, Card, CardContent, Chip, Divider, Grid, MenuItem, Stack, TextField, Typography } from '@mui/material';
import { Download, Logout, Phone, Psychology, Save } from '@mui/icons-material';
import api from '../services/api';

const formatDate = value => value ? new Date(value).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : 'Not set';
const toLocalDateTimeInput = value => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
};

export default function AdminDashboard({ dashboard, complaints, reload, logout }) {
  const [notice, setNotice] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [controls, setControls] = useState({ priority: 'Medium', officialId: '', deadline: '' });
  const stats = dashboard.statistics || {};
  const pendingExtensions = (complaints || []).flatMap(complaint => (complaint.extension_requests || [])
    .filter(request => request.status === 'Pending').map(request => ({ complaint, request })));
  const selected = useMemo(() => complaints.find(item => item.id === selectedId) || complaints[0] || null, [complaints, selectedId]);

  useEffect(() => {
    if (!selected) return;
    setSelectedId(selected.id);
    setControls({ priority: selected.priority || 'Medium', officialId: selected.official_id || '', deadline: toLocalDateTimeInput(selected.sla_due_at) });
  }, [selected?.id, selected?.priority, selected?.official_id, selected?.sla_due_at]);

  const updateOfficial = async (official, approved) => {
    try { await api.patch(`/admin/officials/${official.id}`, { approved }); setNotice({ type: 'success', text: `Official access ${approved ? 'approved' : 'disabled'}.` }); reload(); }
    catch (error) { setNotice({ type: 'error', text: error?.response?.data?.message || 'Unable to update official.' }); }
  };
  const exportComplaints = async () => {
    try { const response = await api.get('/admin/export/complaints', { responseType: 'blob' }); const url = URL.createObjectURL(response.data); const link = document.createElement('a'); link.href = url; link.download = 'civic-complaints.csv'; link.click(); URL.revokeObjectURL(url); }
    catch (error) { setNotice({ type: 'error', text: error?.response?.data?.message || 'Unable to export complaints.' }); }
  };
  const saveControls = async () => {
    if (!selected) return;
    try {
      await api.patch(`/admin/complaints/${selected.id}/manage`, { priority: controls.priority, officialId: controls.officialId || null, ...(controls.deadline ? { deadline: new Date(controls.deadline).toISOString() } : {}) });
      setNotice({ type: 'success', text: `Case #${selected.id} controls updated.` }); reload();
    } catch (error) { setNotice({ type: 'error', text: error?.response?.data?.message || 'Unable to update this case.' }); }
  };
  const reviewEscalation = complaintId => {
    setSelectedId(complaintId);
    window.setTimeout(() => document.getElementById('case-management')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0);
  };

  return <Box sx={{ py: 3 }}>
    <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={2} mb={3}>
      <Box><Typography variant="h4" fontWeight={800}>Administrator portal</Typography><Typography color="text.secondary">System-wide control of citizens, officials, complaints, deadlines, and reports.</Typography>{dashboard.administrator && <Typography variant="caption" color="text.secondary" display="block" mt={.5}>{dashboard.administrator.full_name} · {dashboard.administrator.admin_id} · {dashboard.administrator.department || 'Civic administration'}</Typography>}</Box>
      <Stack direction="row" spacing={1} flexWrap="wrap"><Button startIcon={<Psychology />} onClick={() => window.location.assign('/training')}>AI training</Button><Button startIcon={<Download />} onClick={exportComplaints}>Export CSV</Button><Button color="inherit" startIcon={<Logout />} onClick={logout}>Sign out</Button></Stack>
    </Stack>
    <Grid container spacing={2} mb={3}>{[['Users', stats.totalUsers], ['Officials', stats.totalOfficials], ['Complaints', stats.totalComplaints], ['Critical', stats.criticalComplaints], ['Overdue', stats.overdueComplaints], ['Resolved', stats.resolvedComplaints]].map(([label, value]) => <Grid item xs={6} md={4} lg={2} key={label}><Card><CardContent><Typography variant="caption" color="text.secondary">{label}</Typography><Typography variant="h4" fontWeight={800}>{value ?? 0}</Typography></CardContent></Card></Grid>)}</Grid>
    <Grid container spacing={3}>
      <Grid item xs={12} lg={5}><Card><CardContent><Typography variant="h6" fontWeight={700} mb={2}>Official access</Typography><Stack spacing={1}>{(dashboard.officials || []).map(official => <Stack key={official.id} direction="row" justifyContent="space-between" alignItems="center" sx={{ p: 1, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}><Box><Typography fontWeight={700}>{official.full_name}</Typography><Typography variant="caption" color="text.secondary">{official.department?.name || 'No department'} · {official.approved ? 'Approved' : 'Awaiting approval'}</Typography></Box><Button size="small" color={official.approved ? 'warning' : 'success'} onClick={() => updateOfficial(official, !official.approved)}>{official.approved ? 'Disable' : 'Approve'}</Button></Stack>)}</Stack></CardContent></Card></Grid>
      <Grid item xs={12} lg={7}><Card><CardContent><Typography variant="h6" fontWeight={700} mb={2}>All reported cases</Typography><Stack spacing={.5} sx={{ maxHeight: 360, overflowY: 'auto' }}>{complaints.map(item => <Button key={item.id} color="inherit" onClick={() => setSelectedId(item.id)} sx={{ justifyContent: 'space-between', textAlign: 'left', p: 1.25, borderRadius: 2, bgcolor: selected?.id === item.id ? 'action.selected' : 'transparent' }}><Box><Typography fontWeight={700}>#{item.id} {item.title}</Typography><Typography variant="caption" color="text.secondary">{item.category} · {item.location}</Typography></Box><Stack direction="row" spacing={.5}><Chip size="small" label={item.priority} /><Chip size="small" label={item.status} /></Stack></Button>)}{!complaints.length && <Typography color="text.secondary">No complaints have been filed.</Typography>}</Stack></CardContent></Card></Grid>
    </Grid>
    {(dashboard.slaViolations || []).length > 0 && <Card sx={{ mt: 3, borderColor: 'error.main' }} variant="outlined"><CardContent><Typography variant="h6" fontWeight={750} color="error.main">Overdue cases — administrator action required</Typography><Stack spacing={1} mt={2}>{dashboard.slaViolations.map(item => { const official = (dashboard.officials || []).find(row => row.id === item.official_id); return <Stack key={item.id} direction={{ xs: 'column', md: 'row' }} alignItems={{ md: 'center' }} justifyContent="space-between" spacing={1} sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}><Box><Typography fontWeight={700}>#{item.id} · {item.title}</Typography><Typography variant="body2" color="text.secondary">{item.category} · target {item.sla_target_hours || '—'}h · due {formatDate(item.sla_due_at)} · assigned to {official?.full_name || 'Unassigned'} · {item.status}</Typography></Box><Stack direction="row" spacing={1}><Button size="small" variant="contained" color="warning" onClick={() => reviewEscalation(item.id)}>Review / reassign</Button>{official?.approved && <Button size="small" color="error" onClick={() => updateOfficial(official, false)}>Disable official</Button>}</Stack></Stack>; })}</Stack></CardContent></Card>}
    {pendingExtensions.length > 0 && <Card sx={{ mt: 3 }} variant="outlined"><CardContent><Typography variant="h6" fontWeight={750}>Citizen decisions pending on extra-time requests</Typography><Stack spacing={1} mt={2}>{pendingExtensions.map(({ complaint, request }) => { const official = (dashboard.officials || []).find(row => row.id === request.official_id); return <Stack key={request.id} direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ md: 'center' }} spacing={1} sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}><Box><Typography fontWeight={700}>#{complaint.id} · {complaint.title}</Typography><Typography variant="body2" color="text.secondary">{official?.full_name || 'Official'} asks for {request.requested_hours}h · {request.reason}</Typography><Typography variant="caption" color="text.secondary">Current deadline: {formatDate(complaint.sla_due_at)}</Typography></Box><Button size="small" variant="contained" color="warning" onClick={() => reviewEscalation(complaint.id)}>Review case / reassign</Button></Stack>; })}</Stack></CardContent></Card>}
    {(dashboard.notifications || []).filter(item => (item.message || '').startsWith('Admin action required:')).slice(0, 5).length > 0 && <Card sx={{ mt: 2 }}><CardContent><Typography variant="subtitle1" fontWeight={700}>Admin escalation alerts</Typography><Stack spacing={1} mt={1}>{(dashboard.notifications || []).filter(item => (item.message || '').startsWith('Admin action required:')).slice(0, 5).map(item => <Alert key={item.id} severity="warning">{item.message}</Alert>)}</Stack></CardContent></Card>}
    {selected && <Card id="case-management" sx={{ mt: 3, scrollMarginTop: 24 }}><CardContent><Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={2} mb={2}><Box><Typography variant="h6" fontWeight={750}>Case details · #{selected.id}</Typography><Typography color="text.secondary">Filed {formatDate(selected.created_at)} · Updated {formatDate(selected.updated_at)}</Typography></Box><Stack direction="row" spacing={1}><Chip label={selected.priority} color={selected.priority === 'Critical' ? 'error' : selected.priority === 'High' ? 'warning' : 'info'} /><Chip label={selected.status} /></Stack></Stack><Divider sx={{ mb: 2 }} /><Grid container spacing={3}><Grid item xs={12} md={7}><Typography fontWeight={700}>{selected.title}</Typography><Typography variant="body2" color="text.secondary" mt={.5}>{selected.category} · {selected.location}</Typography><Typography sx={{ whiteSpace: 'pre-wrap', mt: 2 }}>{selected.description}</Typography><Typography variant="body2" color="text.secondary" mt={2}>AI: {selected.ai_category || 'Not available'} {selected.ai_confidence != null ? `(${Math.round(selected.ai_confidence)}% confidence)` : ''}</Typography><Typography variant="subtitle2" mt={2}>Case history</Typography>{(selected.history || []).length ? <Stack spacing={.5} mt={.5}>{selected.history.map(entry => <Typography key={entry.id} variant="body2"><b>{entry.status_name}</b> — {entry.note || 'Status updated'} <Typography component="span" variant="caption" color="text.secondary">({formatDate(entry.created_at)})</Typography></Typography>)}</Stack> : <Typography variant="body2" color="text.secondary">No recorded updates.</Typography>}</Grid><Grid item xs={12} md={5}><Card variant="outlined" sx={{ p: 2, mb: 2 }}><Typography variant="subtitle2">Citizen details — administrator only</Typography><Typography fontWeight={700} mt={1}>{selected.citizen_name || 'Citizen'}</Typography><Stack direction="row" alignItems="center" spacing={.5}><Phone fontSize="small" /><Typography>{selected.citizen_phone || 'No phone supplied'}</Typography></Stack><Typography variant="body2" color="text.secondary" mt={1}>Location: {selected.location}</Typography></Card><Stack spacing={1.5}><TextField select size="small" label="Priority" value={controls.priority} onChange={event => setControls(current => ({ ...current, priority: event.target.value }))}>{['Critical', 'High', 'Medium', 'Low'].map(priority => <MenuItem key={priority} value={priority}>{priority}</MenuItem>)}</TextField><TextField select size="small" label="Assign official" value={controls.officialId} onChange={event => setControls(current => ({ ...current, officialId: event.target.value }))}><MenuItem value="">Unassigned</MenuItem>{(dashboard.officials || []).filter(official => official.approved).map(official => <MenuItem key={official.id} value={official.id}>{official.full_name} — {official.department?.name || 'No department'}</MenuItem>)}</TextField><TextField size="small" label="SLA deadline" type="datetime-local" InputLabelProps={{ shrink: true }} value={controls.deadline} onChange={event => setControls(current => ({ ...current, deadline: event.target.value }))} /><Button variant="contained" startIcon={<Save />} onClick={saveControls}>Save case controls</Button></Stack></Grid></Grid></CardContent></Card>}
    {notice && <Alert sx={{ mt: 2 }} severity={notice.type} onClose={() => setNotice(null)}>{notice.text}</Alert>}
  </Box>;
}
