import React, { useState, useEffect } from 'react';
import { Upload, FileText, Activity, User, Bell, X, Loader2, AlertCircle, Trash2, Eye, Download, RefreshCw, TrendingUp } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ReferenceLine } from 'recharts';

const API_BASE = 'http://localhost:8000';

interface Document {
  id: string;
  filename: string;
  uploadDate: string;
  documentType: string;
  isDiabetesReport?: boolean;
  metrics?: {
    hba1c?: string;
    glucose?: string;
    [key: string]: any;
  };
  rawText?: string;
}

interface Analysis {
  summary: string;
  keyFindings: string[];
  diabetesInfo: string | null;
  recommendations: string[];
  doctorQuestions?: string[];
  criticalAlerts?: string[] | null;
}

interface Trends {
  hasPreviousReport: boolean;
  previousDate: string | null;
  changes: {
    [key: string]: {
      current: string;
      previous: string;
      change: number;
      changePercent: number;
      direction: 'up' | 'down' | 'stable';
      arrow: string;
      isImproving: boolean;
    };
  };
}

function App() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [trends, setTrends] = useState<Trends | null>(null);
  const [severity, setSeverity] = useState<any>(null);
  const [analyzingDoc, setAnalyzingDoc] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [deletingDoc, setDeletingDoc] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'analysis' | 'raw'>('analysis');
  const [showCharts, setShowCharts] = useState(false);
  const [chartData, setChartData] = useState<any>(null);
  const [loadingCharts, setLoadingCharts] = useState(false);

  useEffect(() => {
    fetchDocuments();
    fetchChartData();
  }, []);

  const fetchChartData = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/chart-data`);
      const data = await res.json();
      if (data.success) {
        setChartData(data.data);
      }
    } catch (err) {
      console.error('Failed to fetch chart data:', err);
    }
  };

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/api/documents`);
      const data = await res.json();
      setDocuments(data.sort((a: Document, b: Document) => 
        new Date(b.uploadDate).getTime() - new Date(a.uploadDate).getTime()
      ));
    } catch (err) {
      console.error('Failed to fetch documents:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (file: File) => {
    if (!file) return;

    setUploading(true);
    setErrorMessage(null);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API_BASE}/api/upload-document`, {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();

      if (!data.success) {
        alert(`❌ ${data.message}\n\nReason: ${data.reason}`);
        setErrorMessage(data.message);
        return;
      }

      alert(`✅ Document uploaded successfully!\n${data.validationStatus || ''}`);
      await fetchDocuments();
      
    } catch (err) {
      console.error('Upload failed:', err);
      alert('❌ Upload failed. Check console for details.');
    } finally {
      setUploading(false);
    }
  };

  const deleteDocument = async (docId: string) => {
    if (!confirm('Are you sure you want to delete this document? This action cannot be undone.')) {
      return;
    }

    setDeletingDoc(docId);
    try {
      const res = await fetch(`${API_BASE}/api/documents/${docId}`, {
        method: 'DELETE',
      });

      if (res.ok) {
        alert('✅ Document deleted successfully');
        await fetchDocuments();
      } else {
        alert('❌ Failed to delete document');
      }
    } catch (err) {
      console.error('Delete failed:', err);
      alert('❌ Delete failed. Check console for details.');
    } finally {
      setDeletingDoc(null);
    }
  };

  const viewDocument = async (doc: Document) => {
    setSelectedDoc(doc);
    setViewMode('raw');
    setAnalysis(null);
    setErrorMessage(null);
  };

  const explainDocument = async (doc: Document) => {
    setAnalyzingDoc(doc.id);
    setSelectedDoc(doc);
    setViewMode('analysis');
    setAnalysis(null);
    setErrorMessage(null);

    try {
      const res = await fetch(`${API_BASE}/api/explain-document/${doc.id}`);
      const data = await res.json();

      if (!data.success) {
        setErrorMessage(data.message || 'Analysis failed');
        return;
      }

      if (data.aiAnalysis?.error) {
        setAnalysis({
          summary: data.aiAnalysis.raw?.substring(0, 200) + '...' || 'Analysis failed',
          keyFindings: [],
          diabetesInfo: null,
          recommendations: []
        });
        return;
      }

      const aiAnalysis = typeof data.aiAnalysis === 'string'
        ? JSON.parse(data.aiAnalysis)
        : data.aiAnalysis;

      // Debug: Check what we received
      console.log('=== AI ANALYSIS DEBUG ===');
      console.log('Full response:', data);
      console.log('Doctor Questions:', aiAnalysis.doctorQuestions);
      console.log('Questions length:', aiAnalysis.doctorQuestions?.length);
      console.log('Trends:', data.trends);
      console.log('========================');

      // Set trends data
      if (data.trends) {
        setTrends(data.trends);
      }

      // Set severity data
      if (data.severity) {
        setSeverity(data.severity);
      }

      setAnalysis({
        summary: aiAnalysis.summary || 'No summary available',
        keyFindings: Array.isArray(aiAnalysis.keyFindings) ? aiAnalysis.keyFindings : [],
        diabetesInfo: aiAnalysis.diabetesInfo || null,
        recommendations: Array.isArray(aiAnalysis.recommendations) ? aiAnalysis.recommendations : [],
        doctorQuestions: Array.isArray(aiAnalysis.doctorQuestions) ? aiAnalysis.doctorQuestions : [],
        criticalAlerts: aiAnalysis.criticalAlerts || null
      });

    } catch (err) {
      console.error('Analysis failed:', err);
      setErrorMessage('Failed to load analysis. Please try again.');
    } finally {
      setAnalyzingDoc(null);
    }
  };

  const formatDate = (date: string) => {
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
  };

  const getDocumentTypeLabel = (type: string) => {
    if (type.includes('DIABETES')) return 'DIABETES LAB';
    if (type.includes('DISCHARGE')) return 'DISCHARGE SUMMARY';
    return 'OTHER';
  };

  const getMetricValue = (doc: Document, key: string) => {
    return doc.metrics?.[key] || '—';
  };

  const getSeverityColor = (color: string) => {
    const colors = {
      red: 'bg-red-100 text-red-700 border-red-300',
      yellow: 'bg-yellow-100 text-yellow-700 border-yellow-300',
      green: 'bg-green-100 text-green-700 border-green-300'
    };
    return colors[color as keyof typeof colors] || 'bg-gray-100 text-gray-700 border-gray-300';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-8 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <h1 className="text-xl font-bold text-gray-900">MediTwin Lite</h1>
          </div>
          
          <div className="flex items-center gap-4">
            <button
              onClick={fetchDocuments}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="Refresh documents"
            >
              <RefreshCw className="w-5 h-5 text-gray-600" />
            </button>
            <Bell className="w-5 h-5 text-gray-600 cursor-pointer" />
            <div className="flex items-center gap-3">
              <div className="text-right">
                <div className="font-semibold text-sm text-gray-900">Alex Rivera</div>
                <div className="text-xs text-gray-500">Patient ID: #8621</div>
              </div>
              <div className="w-10 h-10 bg-blue-400 rounded-full flex items-center justify-center">
                <User className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-8 py-8">
        {/* Tab Navigation */}
        <div className="mb-8">
          <div className="border-b border-gray-200">
            <button className="px-1 pb-3 text-blue-600 font-semibold border-b-2 border-blue-600">
              OVERVIEW
            </button>
          </div>
        </div>

        {/* Upload Card - Single, Prominent */}
        <div className="mb-8">
          <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl border-2 border-blue-400 p-8 shadow-lg">
            <div className="flex items-start gap-6">
              <div className="w-16 h-16 bg-white rounded-2xl flex items-center justify-center flex-shrink-0 shadow-md">
                <Upload className="w-8 h-8 text-blue-600" />
              </div>
              
              <div className="flex-1">
                <h3 className="text-2xl font-bold text-white mb-2">Upload Medical Document</h3>
                <p className="text-blue-100 mb-4">
                  Lab reports, prescriptions, discharge summaries, diabetes screenings - we'll automatically detect the type
                </p>
                
                <label className="block cursor-pointer">
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) handleUpload(file);
                    }}
                    disabled={uploading}
                    className="hidden"
                  />
                  <div className="bg-white hover:bg-blue-50 transition-colors rounded-lg p-6 border-2 border-dashed border-blue-300 hover:border-blue-500">
                    {uploading ? (
                      <div className="flex items-center justify-center gap-3">
                        <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />
                        <span className="text-blue-600 font-semibold">Uploading and analyzing...</span>
                      </div>
                    ) : (
                      <div className="flex items-center justify-center gap-3">
                        <FileText className="w-6 h-6 text-blue-600" />
                        <div>
                          <div className="text-blue-600 font-semibold">Click to upload PDF</div>
                          <div className="text-sm text-gray-500">Maximum file size: 10MB</div>
                        </div>
                      </div>
                    )}
                  </div>
                </label>

                <div className="mt-4 flex items-start gap-2 text-blue-100 text-sm">
                  <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <div>
                    <strong className="text-white">Note:</strong> Only medical documents accepted. 
                    Non-medical files (train tickets, invoices) will be automatically rejected.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Health Trends Charts */}
        {chartData && (chartData.hba1c.length > 1 || chartData.glucose.length > 1) && (
          <div className="bg-white rounded-lg border border-gray-200 p-6 mb-8">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-blue-500" />
                <h2 className="text-xl font-bold text-gray-900">Health Trends Over Time</h2>
              </div>
              <button
                onClick={() => setShowCharts(!showCharts)}
                className="text-sm text-blue-600 font-semibold hover:text-blue-700"
              >
                {showCharts ? 'Hide Charts' : 'Show Charts'}
              </button>
            </div>

            {showCharts && (
              <div className="space-y-8">
                {/* HbA1c Chart */}
                {chartData.hba1c.length > 1 && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900 mb-4">HbA1c Trend</h3>
                    <ResponsiveContainer width="100%" height={250}>
                      <LineChart data={chartData.hba1c}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis 
                          dataKey="date" 
                          style={{ fontSize: '12px' }}
                          stroke="#6b7280"
                        />
                        <YAxis 
                          style={{ fontSize: '12px' }}
                          stroke="#6b7280"
                          domain={[4, 'auto']}
                        />
                        <Tooltip 
                          contentStyle={{ 
                            backgroundColor: '#fff', 
                            border: '1px solid #e5e7eb',
                            borderRadius: '8px',
                            fontSize: '12px'
                          }}
                        />
                        <ReferenceLine 
                          y={5.6} 
                          stroke="#10b981" 
                          strokeDasharray="3 3"
                          label={{ value: 'Normal: <5.6%', position: 'right', fill: '#10b981', fontSize: 11 }}
                        />
                        <ReferenceLine 
                          y={6.5} 
                          stroke="#f59e0b" 
                          strokeDasharray="3 3"
                          label={{ value: 'Prediabetes: 5.7-6.4%', position: 'right', fill: '#f59e0b', fontSize: 11 }}
                        />
                        <Line 
                          type="monotone" 
                          dataKey="value" 
                          stroke="#3b82f6" 
                          strokeWidth={3}
                          dot={{ fill: '#3b82f6', r: 5 }}
                          activeDot={{ r: 7 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}

                {/* Glucose Chart */}
                {chartData.glucose.length > 1 && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900 mb-4">Fasting Glucose Trend</h3>
                    <ResponsiveContainer width="100%" height={250}>
                      <LineChart data={chartData.glucose}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis 
                          dataKey="date" 
                          style={{ fontSize: '12px' }}
                          stroke="#6b7280"
                        />
                        <YAxis 
                          style={{ fontSize: '12px' }}
                          stroke="#6b7280"
                          domain={[60, 'auto']}
                        />
                        <Tooltip 
                          contentStyle={{ 
                            backgroundColor: '#fff', 
                            border: '1px solid #e5e7eb',
                            borderRadius: '8px',
                            fontSize: '12px'
                          }}
                        />
                        <ReferenceLine 
                          y={100} 
                          stroke="#10b981" 
                          strokeDasharray="3 3"
                          label={{ value: 'Normal: <100 mg/dL', position: 'right', fill: '#10b981', fontSize: 11 }}
                        />
                        <ReferenceLine 
                          y={126} 
                          stroke="#ef4444" 
                          strokeDasharray="3 3"
                          label={{ value: 'Diabetes: ≥126 mg/dL', position: 'right', fill: '#ef4444', fontSize: 11 }}
                        />
                        <Line 
                          type="monotone" 
                          dataKey="value" 
                          stroke="#8b5cf6" 
                          strokeWidth={3}
                          dot={{ fill: '#8b5cf6', r: 5 }}
                          activeDot={{ r: 7 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}

                {/* Blood Pressure Chart */}
                {chartData.blood_pressure.length > 1 && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900 mb-4">Blood Pressure Trend (Systolic)</h3>
                    <ResponsiveContainer width="100%" height={250}>
                      <LineChart data={chartData.blood_pressure}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis 
                          dataKey="date" 
                          style={{ fontSize: '12px' }}
                          stroke="#6b7280"
                        />
                        <YAxis 
                          style={{ fontSize: '12px' }}
                          stroke="#6b7280"
                          domain={[100, 'auto']}
                        />
                        <Tooltip 
                          contentStyle={{ 
                            backgroundColor: '#fff', 
                            border: '1px solid #e5e7eb',
                            borderRadius: '8px',
                            fontSize: '12px'
                          }}
                        />
                        <ReferenceLine 
                          y={120} 
                          stroke="#10b981" 
                          strokeDasharray="3 3"
                          label={{ value: 'Normal: <120 mmHg', position: 'right', fill: '#10b981', fontSize: 11 }}
                        />
                        <ReferenceLine 
                          y={140} 
                          stroke="#ef4444" 
                          strokeDasharray="3 3"
                          label={{ value: 'Hypertension: ≥140 mmHg', position: 'right', fill: '#ef4444', fontSize: 11 }}
                        />
                        <Line 
                          type="monotone" 
                          dataKey="value" 
                          stroke="#f59e0b" 
                          strokeWidth={3}
                          dot={{ fill: '#f59e0b', r: 5 }}
                          activeDot={{ r: 7 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}

                {/* Cholesterol Chart */}
                {chartData.cholesterol.length > 1 && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900 mb-4">Total Cholesterol Trend</h3>
                    <ResponsiveContainer width="100%" height={250}>
                      <LineChart data={chartData.cholesterol}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis 
                          dataKey="date" 
                          style={{ fontSize: '12px' }}
                          stroke="#6b7280"
                        />
                        <YAxis 
                          style={{ fontSize: '12px' }}
                          stroke="#6b7280"
                          domain={[150, 'auto']}
                        />
                        <Tooltip 
                          contentStyle={{ 
                            backgroundColor: '#fff', 
                            border: '1px solid #e5e7eb',
                            borderRadius: '8px',
                            fontSize: '12px'
                          }}
                        />
                        <ReferenceLine 
                          y={200} 
                          stroke="#10b981" 
                          strokeDasharray="3 3"
                          label={{ value: 'Desirable: <200 mg/dL', position: 'right', fill: '#10b981', fontSize: 11 }}
                        />
                        <Line 
                          type="monotone" 
                          dataKey="value" 
                          stroke="#ec4899" 
                          strokeWidth={3}
                          dot={{ fill: '#ec4899', r: 5 }}
                          activeDot={{ r: 7 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Document History */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-gray-900">Medical Document History</h2>
            <div className="flex gap-2">
              <button 
                onClick={fetchDocuments}
                className="text-sm text-blue-600 font-semibold hover:text-blue-700 flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh
              </button>
            </div>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
            </div>
          ) : documents.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500 mb-2">No documents uploaded yet</p>
              <p className="text-sm text-gray-400">Upload your first medical document above to get started</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-900">Document</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-900">Type</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-900">Date</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-900">Metrics</th>
                    <th className="text-center py-3 px-4 text-sm font-semibold text-gray-900">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((doc) => (
                    <tr key={doc.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-4 px-4">
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-blue-500 flex-shrink-0" />
                          <span className="text-sm text-gray-900 truncate max-w-xs">{doc.filename}</span>
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        <span className="inline-block px-3 py-1 bg-gray-100 text-gray-700 text-xs font-semibold rounded">
                          {getDocumentTypeLabel(doc.documentType)}
                        </span>
                      </td>
                      <td className="py-4 px-4 text-sm text-gray-600">
                        {formatDate(doc.uploadDate)}
                      </td>
                      <td className="py-4 px-4">
                        <div className="flex gap-2 text-xs">
                          {doc.isDiabetesReport && (
                            <>
                              <span className="text-gray-600">
                                HbA1c: <span className="font-semibold">{getMetricValue(doc, 'hba1c')}</span>
                              </span>
                              <span className="text-gray-400">|</span>
                              <span className="text-gray-600">
                                Glucose: <span className="font-semibold">{getMetricValue(doc, 'glucose')}</span>
                              </span>
                            </>
                          )}
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        <div className="flex items-center justify-center gap-2">
                          <button
                            onClick={() => viewDocument(doc)}
                            className="p-2 hover:bg-blue-50 rounded text-blue-600 transition-colors"
                            title="View document content"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => explainDocument(doc)}
                            disabled={analyzingDoc === doc.id}
                            className="px-3 py-1 text-sm text-blue-600 font-semibold hover:bg-blue-50 rounded transition-colors disabled:opacity-50"
                            title="Get AI analysis"
                          >
                            {analyzingDoc === doc.id ? 'Analyzing...' : 'Analyze'}
                          </button>
                          <button
                            onClick={() => deleteDocument(doc.id)}
                            disabled={deletingDoc === doc.id}
                            className="p-2 hover:bg-red-50 rounded text-red-600 transition-colors disabled:opacity-50"
                            title="Delete document"
                          >
                            {deletingDoc === doc.id ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <Trash2 className="w-4 h-4" />
                            )}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>

      {/* Document Modal */}
      {selectedDoc && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* Modal Header */}
            <div className="bg-blue-500 p-6 relative">
              <button
                onClick={() => {
                  setSelectedDoc(null);
                  setAnalysis(null);
                  setErrorMessage(null);
                }}
                className="absolute top-4 right-4 text-white hover:bg-blue-600 rounded p-1"
              >
                <X className="w-5 h-5" />
              </button>
              
              <div className="flex items-start gap-4">
                <FileText className="w-12 h-12 text-white opacity-50 flex-shrink-0" />
                <div className="flex-1">
                  <div className="text-xs text-blue-100 mb-1">
                    {formatDate(selectedDoc.uploadDate)}
                  </div>
                  <h2 className="text-2xl font-bold text-white mb-1">
                    {viewMode === 'analysis' ? 'AI Analysis' : 'Document Content'}
                  </h2>
                  <p className="text-blue-100 text-sm truncate">{selectedDoc.filename}</p>
                </div>
              </div>

              {/* View Mode Tabs */}
              <div className="flex gap-2 mt-4">
                <button
                  onClick={() => setViewMode('analysis')}
                  className={`px-4 py-2 rounded text-sm font-semibold transition-colors ${
                    viewMode === 'analysis'
                      ? 'bg-white text-blue-600'
                      : 'bg-blue-400 text-white hover:bg-blue-600'
                  }`}
                >
                  <Activity className="w-4 h-4 inline mr-2" />
                  AI Analysis
                </button>
                <button
                  onClick={() => setViewMode('raw')}
                  className={`px-4 py-2 rounded text-sm font-semibold transition-colors ${
                    viewMode === 'raw'
                      ? 'bg-white text-blue-600'
                      : 'bg-blue-400 text-white hover:bg-blue-600'
                  }`}
                >
                  <FileText className="w-4 h-4 inline mr-2" />
                  Raw Text
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto flex-1">
              {viewMode === 'raw' ? (
                // Raw Text View
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-semibold text-gray-900">Extracted Text Content</h3>
                    <button
                      onClick={() => {
                        if (selectedDoc.rawText) {
                          navigator.clipboard.writeText(selectedDoc.rawText);
                          alert('✅ Text copied to clipboard!');
                        }
                      }}
                      className="text-sm text-blue-600 hover:text-blue-700"
                    >
                      Copy Text
                    </button>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4 font-mono text-xs text-gray-700 whitespace-pre-wrap max-h-96 overflow-y-auto border border-gray-200">
                    {selectedDoc.rawText || 'No text content available'}
                  </div>
                </div>
              ) : errorMessage ? (
                // Error View
                <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <h3 className="text-lg font-semibold text-red-900 mb-2">
                        Analysis Not Available
                      </h3>
                      <p className="text-sm text-red-700 mb-3">{errorMessage}</p>
                      <p className="text-xs text-red-600">
                        This document may be non-medical (train ticket, invoice, etc.). Please upload medical documents only.
                      </p>
                    </div>
                  </div>
                </div>
              ) : !analysis ? (
                // Loading View
                <div className="flex flex-col items-center justify-center py-12">
                  <Loader2 className="w-12 h-12 text-blue-500 animate-spin mb-4" />
                  <p className="text-gray-600">Analyzing document with AI...</p>
                </div>
              ) : (
                // Analysis View
                <div className="space-y-6">
                  {/* Improvement Banner - Show if trends are improving */}
                  {trends?.hasPreviousReport && (
                    (() => {
                      const improvingMetrics = Object.entries(trends.changes).filter(
                        ([_, change]: any) => change.isImproving
                      );
                      
                      if (improvingMetrics.length > 0) {
                        return (
                          <div className="bg-green-50 border-2 border-green-300 rounded-lg p-4 shadow-sm">
                            <div className="flex items-start gap-3">
                              <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center flex-shrink-0">
                                <Activity className="w-5 h-5 text-white" />
                              </div>
                              <div className="flex-1">
                                <h3 className="text-sm font-bold text-green-900 mb-2">
                                  ✅ GREAT PROGRESS! Your health is improving!
                                </h3>
                                <div className="space-y-1">
                                  {improvingMetrics.map(([metric, change]: any) => (
                                    <p key={metric} className="text-sm text-green-800 font-medium">
                                      • {metric.toUpperCase()}: {change.current} 
                                      <span className="text-green-600 font-bold"> ↓ {Math.abs(change.change)}</span>
                                      {metric === 'hba1c' ? '%' : metric === 'glucose' ? ' mg/dL' : ''} from {change.previous}
                                    </p>
                                  ))}
                                </div>
                                <p className="text-xs text-green-700 mt-2">
                                  Keep up the great work! Continue your current treatment plan.
                                </p>
                              </div>
                            </div>
                          </div>
                        );
                      }
                      return null;
                    })()
                  )}

                  {/* Critical Alerts Banner - Show First if Present */}
                  {severity?.criticalAlerts && severity.criticalAlerts.length > 0 && (
                    <div className="bg-red-50 border-2 border-red-300 rounded-lg p-4 shadow-sm">
                      <div className="flex items-start gap-3">
                        <AlertCircle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
                        <div className="flex-1">
                          <h3 className="text-sm font-bold text-red-900 mb-2">⚠️ HEALTH ALERTS</h3>
                          <ul className="space-y-1">
                            {severity.criticalAlerts.map((alert: string, i: number) => (
                              <li key={i} className="text-sm text-red-800 font-medium">
                                {alert}
                              </li>
                            ))}
                          </ul>
                          <p className="text-xs text-red-700 mt-2 font-semibold">
                            Please discuss these results with your doctor.
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Metrics with Trends and Severity Badges */}
                  {selectedDoc.isDiabetesReport && (
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-4">
                        {/* HbA1c Card */}
                        <div className="border-2 border-gray-200 rounded-lg p-4">
                          <div className="text-xs font-semibold text-gray-600 mb-1">HBA1C</div>
                          <div className="text-2xl font-bold text-gray-900 mb-2">
                            {getMetricValue(selectedDoc, 'hba1c')}
                          </div>
                          {severity?.severity?.hba1c && (
                            <div className={`inline-block px-2 py-1 rounded text-xs font-bold border ${
                              getSeverityColor(severity.severity.hba1c.color)
                            }`}>
                              {severity.severity.hba1c.label}
                            </div>
                          )}
                          {trends?.changes?.hba1c && (
                            <div className={`text-xs mt-2 flex items-center gap-1 ${
                              trends.changes.hba1c.isImproving ? 'text-green-600' : 'text-red-600'
                            }`}>
                              <span className="text-base font-bold">{trends.changes.hba1c.arrow}</span>
                              <span className="font-semibold">
                                {Math.abs(trends.changes.hba1c.change)}% from {trends.changes.hba1c.previous}
                              </span>
                              {trends.changes.hba1c.isImproving && (
                                <span className="ml-1 text-xs font-bold">✅ IMPROVING</span>
                              )}
                            </div>
                          )}
                        </div>

                        {/* Glucose Card */}
                        <div className="border-2 border-gray-200 rounded-lg p-4">
                          <div className="text-xs font-semibold text-gray-600 mb-1">GLUCOSE</div>
                          <div className="text-2xl font-bold text-gray-900 mb-2">
                            {getMetricValue(selectedDoc, 'glucose')}
                          </div>
                          {severity?.severity?.glucose && (
                            <div className={`inline-block px-2 py-1 rounded text-xs font-bold border ${
                              getSeverityColor(severity.severity.glucose.color)
                            }`}>
                              {severity.severity.glucose.label}
                            </div>
                          )}
                          {trends?.changes?.glucose && (
                            <div className={`text-xs mt-2 flex items-center gap-1 ${
                              trends.changes.glucose.isImproving ? 'text-green-600' : 'text-red-600'
                            }`}>
                              <span className="text-base font-bold">{trends.changes.glucose.arrow}</span>
                              <span className="font-semibold">
                                {Math.abs(trends.changes.glucose.change)} mg/dL from {trends.changes.glucose.previous}
                              </span>
                              {trends.changes.glucose.isImproving && (
                                <span className="ml-1 text-xs font-bold">✅ IMPROVING</span>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                      
                      {/* Trend Summary Banner */}
                      {trends?.hasPreviousReport && (
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                          <div className="flex items-start gap-2">
                            <Activity className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
                            <div className="text-xs text-blue-800">
                              <span className="font-semibold">Compared with previous report </span>
                              {trends.previousDate && (
                                <span className="text-blue-600">
                                  from {new Date(trends.previousDate).toLocaleDateString()}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* AI Summary */}
                  <div>
                    <h3 className="text-sm font-semibold text-blue-600 mb-2">AI SUMMARY</h3>
                    <p className="text-sm text-gray-700 bg-blue-50 p-4 rounded-lg leading-relaxed">
                      {analysis.summary}
                    </p>
                  </div>

                  {/* Doctor Questions - PROMINENT SECTION */}
                  {analysis.doctorQuestions && analysis.doctorQuestions.length > 0 && (
                    <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-5 border-2 border-blue-200">
                      <div className="flex items-start gap-3 mb-4">
                        <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center flex-shrink-0">
                          <User className="w-6 h-6 text-white" />
                        </div>
                        <div>
                          <h3 className="text-base font-bold text-gray-900">Smart Questions for Your Doctor</h3>
                          <p className="text-xs text-gray-600 mt-1">
                            Ask these specific questions based on your results
                          </p>
                        </div>
                      </div>
                      <ol className="space-y-3">
                        {analysis.doctorQuestions.map((question, i) => (
                          <li key={i} className="flex items-start gap-3 bg-white p-3 rounded-lg shadow-sm">
                            <span className="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-bold">
                              {i + 1}
                            </span>
                            <span className="text-sm text-gray-800 font-medium leading-relaxed pt-0.5">
                              {question}
                            </span>
                          </li>
                        ))}
                      </ol>
                    </div>
                  )}

                  {/* Key Findings */}
                  {analysis.keyFindings && analysis.keyFindings.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold text-gray-900 mb-3">KEY FINDINGS</h3>
                      <ul className="space-y-2">
                        {analysis.keyFindings.map((finding, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-gray-700 bg-gray-50 p-3 rounded">
                            <span className="text-blue-500 mt-1">•</span>
                            <span>{finding}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Recommendations */}
                  {analysis.recommendations && analysis.recommendations.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-3">
                        <Activity className="w-5 h-5 text-green-600" />
                        <h3 className="text-sm font-semibold text-gray-900">ACTION STEPS</h3>
                      </div>
                      <ol className="space-y-2">
                        {analysis.recommendations.map((rec, i) => (
                          <li key={i} className="flex items-start gap-3 text-sm text-gray-700">
                            <span className="text-green-600 font-semibold">{i + 1}.</span>
                            <span>{rec}</span>
                          </li>
                        ))}
                      </ol>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="border-t border-gray-200 p-4 flex gap-2">
              <button
                onClick={() => {
                  setSelectedDoc(null);
                  setAnalysis(null);
                  setErrorMessage(null);
                }}
                className="flex-1 py-2 bg-gray-100 text-gray-900 font-semibold rounded-lg hover:bg-gray-200 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function UploadCard({ 
  title, 
  subtitle, 
  description, 
  icon, 
  onUpload,
  uploading 
}: { 
  title: string;
  subtitle: string;
  description: string;
  icon: React.ReactNode;
  onUpload: (file: File) => void;
  uploading: boolean;
}) {
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onUpload(file);
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center gap-2 mb-6">
        {icon}
        <h3 className="font-bold text-gray-900">{title}</h3>
      </div>

      <label className="block cursor-pointer">
        <input
          type="file"
          accept=".pdf"
          onChange={handleFileChange}
          disabled={uploading}
          className="hidden"
        />
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 hover:bg-blue-50 transition-colors">
          {uploading ? (
            <Loader2 className="w-12 h-12 text-blue-500 mx-auto mb-3 animate-spin" />
          ) : (
            <Upload className="w-12 h-12 text-blue-400 mx-auto mb-3" />
          )}
          <div className="font-semibold text-gray-900 mb-1">{subtitle}</div>
          <div className="text-sm text-gray-500">{description}</div>
        </div>
      </label>
    </div>
  );
}

export default App;