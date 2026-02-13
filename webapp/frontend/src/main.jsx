import React from 'react'
import ReactDOM from 'react-dom/client'
import {
  Alert,
  AppBar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Container,
  CssBaseline,
  Divider,
  List,
  ListItem,
  ListItemText,
  Stack,
  TextField,
  Toolbar,
  Typography,
} from '@mui/material'
import SportsScoreIcon from '@mui/icons-material/SportsScore'

function extractRanking(reportText) {
  return reportText
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => /^\d+位\s\|/.test(line))
}

function App() {
  const [raceId, setRaceId] = React.useState('')
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState('')
  const [result, setResult] = React.useState(null)
  const [history, setHistory] = React.useState([])

  const onSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!/^\d{12}$/.test(raceId)) {
      setError('race_id は12桁の数字で入力してください')
      return
    }

    setLoading(true)
    try {
      const res = await fetch('http://127.0.0.1:8000/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ race_id: raceId }),
      })

      if (!res.ok) {
        const payload = await res.json()
        throw new Error(payload.detail || '予測に失敗しました')
      }

      const data = await res.json()
      setResult(data)
      setHistory((prev) => [data.race_id, ...prev.filter((id) => id !== data.race_id)].slice(0, 5))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const ranking = result ? extractRanking(result.report_text) : []

  return (
    <>
      <CssBaseline />
      <AppBar position="static">
        <Toolbar>
          <SportsScoreIcon sx={{ mr: 1 }} />
          <Typography variant="h6">競馬予想AI ローカルダッシュボード</Typography>
        </Toolbar>
      </AppBar>

      <Container sx={{ py: 4 }} maxWidth="md">
        <Card>
          <CardContent>
            <Stack component="form" spacing={2} onSubmit={onSubmit}>
              <Typography variant="h6">race_id から予測レポートを生成</Typography>
              <TextField
                label="race_id（12桁）"
                value={raceId}
                onChange={(e) => setRaceId(e.target.value)}
                placeholder="例: 202406050811"
              />
              <Button type="submit" variant="contained" disabled={loading}>
                {loading ? <CircularProgress size={24} /> : '予測実行'}
              </Button>
              {error && <Alert severity="error">{error}</Alert>}
            </Stack>
          </CardContent>
        </Card>

        <Box sx={{ mt: 3 }}>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>最近実行した race_id</Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap">
            {history.length === 0 && <Chip label="まだ実行履歴はありません" />}
            {history.map((id) => (
              <Chip key={id} label={id} onClick={() => setRaceId(id)} />
            ))}
          </Stack>
        </Box>

        {result && (
          <Card sx={{ mt: 3 }}>
            <CardContent>
              <Typography variant="h6">予測結果</Typography>
              <Typography variant="body2" color="text.secondary">
                Report: {result.report_path}
              </Typography>

              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle1">モデル順位</Typography>
              <List dense>
                {ranking.map((line) => (
                  <ListItem key={line}>
                    <ListItemText primary={line} />
                  </ListItem>
                ))}
              </List>

              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle1">レポート全文</Typography>
              <Box component="pre" sx={{ whiteSpace: 'pre-wrap', fontSize: 13, bgcolor: '#fafafa', p: 2, borderRadius: 1 }}>
                {result.report_text}
              </Box>
            </CardContent>
          </Card>
        )}
      </Container>
    </>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
