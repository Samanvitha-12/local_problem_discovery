import React, { useEffect, useState } from 'react';
import { Alert, Box, Button, Card, CardContent, Chip, Grid, LinearProgress, MenuItem, Stack, TextField, Typography } from '@mui/material';
import { ArrowBack, CloudUpload, ModelTraining, Storage } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useTranslation } from 'react-i18next';

export default function TrainingPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState(null);
  const [dataset, setDataset] = useState([]);
  const [complaintFile, setComplaintFile] = useState(null);
  const [category, setCategory] = useState('Road Damage');
  const [message, setMessage] = useState('');
  const [trainingBusy, setTrainingBusy] = useState(false);
  const [detectorBusy, setDetectorBusy] = useState(false);
  const complaintDataset = metrics?.complaintDataset;
  const complaintSamples = complaintDataset?.samples || [];
  const datasetHealth = metrics?.datasetHealth;

  const fetchMetrics = async () => {
    try {
      const r = await api.get('/ai/training/metrics');
      setMetrics(r.data.data.metrics);
    } catch (e) {
      setMessage(e.message || 'Only administrators can access model training.');
    }
  };

  useEffect(() => {
    fetchMetrics();
    const refreshTimer = window.setInterval(fetchMetrics, 5000);
    return () => window.clearInterval(refreshTimer);
  }, []);

  const upload = async () => {
    if (!dataset.length) return setMessage('Select dataset images first.');
    const data = new FormData();
    data.append('category', category);
    dataset.forEach(file => data.append('files', file));
    try {
      const result = await api.post('/ai/training/dataset', data);
      setMetrics(m => ({ ...m, dataset: result.data.data.dataset }));
      setMessage(`${result.data.data.saved} labelled images added to ${category}.`);
      setDataset([]);
    } catch (e) {
      setMessage(e.message);
    }
  };

  const trainModel = async () => {
    setTrainingBusy(true);
    setMessage('Training AI model on complaint dataset...');
    try {
      const res = await api.post('/ai/training/train');
      setMessage(res.data.message || 'Model training finished successfully.');
      await fetchMetrics();
    } catch (e) {
      setMessage(e.message || 'Training failed.');
    } finally {
      setTrainingBusy(false);
    }
  };

  const trainDetector = async () => {
    setDetectorBusy(true);
    setMessage('Starting YOLO detector training from the labelled civic dataset...');
    try {
      const res = await api.post('/ai/training/yolo', { epochs: 100 });
      setMessage(res.data.message || 'YOLO training started. Progress is shown below.');
      await fetchMetrics();
    } catch (e) {
      setMessage(e.message || 'YOLO training could not start. Add valid YOLO labels first.');
    } finally {
      setDetectorBusy(false);
    }
  };

  const uploadComplaintDataset = async () => {
    if (!complaintFile) return setMessage('Select a complaint CSV first.');
    const data = new FormData();
    data.append('file', complaintFile);
    try {
      const result = await api.post('/ai/training/complaint-dataset', data);
      setMetrics(m => ({ ...m, complaintDataset: result.data.data.complaintDataset, sampleCount: result.data.data.complaintDataset.sampleCount }));
      setMessage(`${result.data.data.saved} complaint records added. Select Train AI Model to apply them.`);
      setComplaintFile(null);
    } catch (e) {
      setMessage(e.message || 'Could not add the complaint dataset.');
    }
  };

  return (
    <Box sx={{ py: 3, maxWidth: 1100, mx: 'auto' }}>
      <Button startIcon={<ArrowBack />} onClick={() => navigate('/dashboard')}>
        {t('back')}
      </Button>

      <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ md: 'center' }} mt={2} mb={3} gap={2}>
        <Box>
          <Typography variant="h4" fontWeight={800}>{t('training')}</Typography>
          <Typography color="text.secondary">
            Manage complaint datasets ({metrics?.sampleCount || 0} labelled records loaded) and monitor model metrics.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center">
          <Chip icon={<ModelTraining />} label={metrics?.status || 'Loading'} color="primary" />
          <Chip size="small" label="Live · refreshes every 5 sec" variant="outlined" />
          <Button variant="contained" color="secondary" startIcon={<ModelTraining />} onClick={trainModel} disabled={trainingBusy}>
            {trainingBusy ? 'Training...' : 'Train AI Model'}
          </Button>
          <Button variant="contained" startIcon={<ModelTraining />} onClick={trainDetector} disabled={detectorBusy || metrics?.detectorTraining?.state === 'running'}>
            {metrics?.detectorTraining?.state === 'running' ? 'Detector training...' : 'Train YOLO Detector'}
          </Button>
        </Stack>
      </Stack>

      {message && <Alert severity="info" sx={{ mb: 2 }}>{message}</Alert>}

      <Grid container spacing={3}>
        <Grid item xs={12} md={7}>
          <Card sx={{ borderRadius: 4 }}>
            <CardContent>
              <Typography variant="h6" fontWeight={750}>{t('datasetIntake')}</Typography>
              <Typography variant="body2" color="text.secondary" mt={1}>
                Upload labelled JPG/PNG images by category. Complaint-text records and image uploads are tracked separately for accurate AI training results.
              </Typography>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} mt={3}>
                <TextField select label={t('category')} value={category} onChange={e => setCategory(e.target.value)} sx={{ minWidth: 160 }}>
                  {Object.keys(metrics?.dataset || { 'Road Damage': 0, Garbage: 0 }).map(c => (
                    <MenuItem key={c} value={c}>{c}</MenuItem>
                  ))}
                </TextField>
                <Button component="label" variant="outlined" startIcon={<CloudUpload />}>
                  {t('selectDataset')}
                  <input hidden multiple type="file" accept=".jpg,.jpeg,.jpe,.jfif,.png,.apng,.webp,.bmp,.dib,.tif,.tiff,.gif,.avif,.jp2,.j2k,.ico,.tga" onChange={e => setDataset(Array.from(e.target.files || []))} />
                </Button>
                <Button variant="contained" onClick={upload} disabled={!dataset.length}>
                  Upload
                </Button>
              </Stack>
              {dataset.length > 0 && <Typography mt={2}>{dataset.length} image files ready to upload.</Typography>}
              <Box mt={3}>
                <Typography variant="subtitle2" fontWeight={700} mb={1}>Uploaded image distribution:</Typography>
                <Typography variant="body2" color="text.secondary">
                  {Object.entries(metrics?.dataset || {}).map(([name, count]) => `${name} (${count})`).join(' · ') || 'Loading'}
                </Typography>
              </Box>
              <Box mt={3}>
                <Typography variant="subtitle2" fontWeight={700} mb={1}>
                  Image training readiness (minimum {datasetHealth?.minimumImagesPerClass || 10} images per category)
                </Typography>
                <Stack direction="row" gap={.75} flexWrap="wrap">
                  {Object.entries(datasetHealth?.categories || {}).map(([name, info]) => (
                    <Chip key={name} size="small" color={info.trainReady ? 'success' : 'warning'} label={`${name}: ${info.images}${info.trainReady ? ' ready' : ` · add ${info.needed}`}`} />
                  ))}
                </Stack>
                <Typography variant="body2" color="text.secondary" mt={1}>
                  Raw folders: {(datasetHealth?.rawFolders || []).join(', ') || 'none'} · Processed folders: {(datasetHealth?.processedFolders || []).join(', ') || 'none'}
                </Typography>
                <Typography variant="caption" color="text.secondary">{datasetHealth?.rawPolicy}</Typography>
              </Box>
              <Box mt={3}>
                <Typography variant="subtitle2" fontWeight={700} mb={1}>Real-time civic detector</Typography>
                <Typography variant="body2" color="text.secondary">
                  Status: {metrics?.detector?.ready ? 'Deployed and ready' : (metrics?.detector?.error || 'No detector deployed')}
                </Typography>
                <Typography variant="body2" color="text.secondary" mt={.75}>
                  Training: {metrics?.detectorTraining?.state || 'idle'}{metrics?.detectorTraining?.finished_at ? ` · finished ${new Date(metrics.detectorTraining.finished_at).toLocaleString()}` : ''}
                </Typography>
                {metrics?.detectorTraining?.state === 'failed' && <Typography variant="caption" color="error">{metrics.detectorTraining.output?.slice(-500)}</Typography>}
                <Typography variant="caption" display="block" color="text.secondary" mt={1}>
                  Detector training uses only datasets/civic_yolo images with matching YOLO bounding-box labels. Image-only uploads cannot be used as detection training data.
                </Typography>
              </Box>
              <Box mt={3}>
                <Typography variant="subtitle2" fontWeight={700} mb={1}>Add complaint records (CSV):</Typography>
                <Typography variant="body2" color="text.secondary" mb={1}>
                  Required headers: complaint_text, category, priority. Priority must be Critical, High, Medium, or Low.
                </Typography>
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                  <Button component="label" variant="outlined" startIcon={<CloudUpload />}>
                    Select complaint CSV
                    <input hidden type="file" accept=".csv,text/csv" onChange={e => setComplaintFile(e.target.files?.[0] || null)} />
                  </Button>
                  <Button variant="contained" onClick={uploadComplaintDataset} disabled={!complaintFile}>
                    Add records
                  </Button>
                </Stack>
                {complaintFile && <Typography variant="body2" mt={1}>{complaintFile.name} ready to add.</Typography>}
              </Box>
              <Box mt={3}>
                <Typography variant="subtitle2" fontWeight={700} mb={1}>
                  Complaint dataset: {complaintDataset?.sampleCount ?? 0} labelled records
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Categories: {Object.entries(complaintDataset?.categoryDistribution || {}).map(([name, count]) => `${name} (${count})`).join(' · ') || 'No complaint records found'}
                </Typography>
                <Typography variant="body2" color="text.secondary" mt={.75}>
                  Priority labels: {Object.entries(complaintDataset?.priorityDistribution || {}).map(([name, count]) => `${name} (${count})`).join(' · ') || 'No priority labels found'}
                </Typography>
                {complaintSamples.length > 0 && (
                  <Box mt={2}>
                    <Typography variant="subtitle2" fontWeight={700} mb={1}>Preview of complaint examples</Typography>
                    <Stack spacing={1}>
                      {complaintSamples.map((sample, index) => (
                        <Box key={`${sample.category}-${index}`} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 1.25 }}>
                          <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ sm: 'center' }} gap={1}>
                            <Typography variant="body2" fontWeight={700}>{sample.category} · {sample.priority}</Typography>
                            <Typography variant="caption" color="text.secondary">{sample.source || 'Imported dataset'}</Typography>
                          </Stack>
                          <Typography variant="body2" color="text.secondary" mt={0.75}>{sample.complaint_text}</Typography>
                          {sample.location_hint && <Typography variant="caption" color="text.secondary">Location hint: {sample.location_hint}</Typography>}
                        </Box>
                      ))}
                    </Stack>
                  </Box>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={5}>
          <Card sx={{ borderRadius: 4 }}>
            <CardContent>
              <Stack direction="row" spacing={1} alignItems="center">
                <Storage color="primary" />
                <Typography variant="h6" fontWeight={750}>{t('modelMetrics')}</Typography>
              </Stack>

              {[
                ['Category classification accuracy', metrics?.accuracy],
                ['Priority classification accuracy', metrics?.validationAccuracy],
                ['Precision score', metrics?.precision],
                ['Recall score', metrics?.recall],
                ['F1 performance score', metrics?.f1],
              ].map(([label, value]) => (
                <Box mt={2} key={label}>
                  <Stack direction="row" justifyContent="space-between">
                    <Typography variant="body2">{label}</Typography>
                    <Typography variant="body2" fontWeight={700}>
                      {typeof value === 'number' ? `${Math.round(value * 100)}%` : 'Awaiting training'}
                    </Typography>
                  </Stack>
                  <LinearProgress variant="determinate" value={(value || 0) * 100} sx={{ mt: .5, borderRadius: 3, height: 8 }} />
                </Box>
              ))}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
