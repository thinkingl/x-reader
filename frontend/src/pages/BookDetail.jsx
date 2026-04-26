import React, { useState, useEffect, useContext, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { Table, Button, Select, message, Space, Tag, Card, Descriptions, Tooltip, Progress, Modal } from 'antd';
import { PlayCircleOutlined, ReloadOutlined, AudioOutlined, SyncOutlined, ClockCircleOutlined, DownloadOutlined, EyeOutlined } from '@ant-design/icons';
import api from '../api';
import { AudioContext } from '../components/AudioPlayer';

function BookDetail() {
  const { id } = useParams();
  const [book, setBook] = useState(null);
  const [chapters, setChapters] = useState([]);
  const [presets, setPresets] = useState([]);
  const [selectedPreset, setSelectedPreset] = useState(() => {
    const saved = localStorage.getItem('selectedPreset');
    return saved ? parseInt(saved) : null;
  });
  const [loading, setLoading] = useState(false);
  const [downloadingZip, setDownloadingZip] = useState(false);
  const [downloadingChapter, setDownloadingChapter] = useState(null);
  const [taskProgress, setTaskProgress] = useState({});  // {taskId: {message, elapsed}}
  const { playAudio } = useContext(AudioContext);
  const progressInterval = useRef(null);
  
  // 章节内容查看
  const [viewModalVisible, setViewModalVisible] = useState(false);
  const [viewChapter, setViewChapter] = useState(null);
  const [viewContent, setViewContent] = useState('');
  const [viewLoading, setViewLoading] = useState(false);

  const handlePresetChange = (value) => {
    setSelectedPreset(value);
    if (value === null) {
      localStorage.removeItem('selectedPreset');
    } else {
      localStorage.setItem('selectedPreset', value);
    }
  };

  useEffect(() => {
    fetchBook();
    fetchChapters();
    fetchPresets();

    // 定期刷新章节状态（每2秒）
    const chapterInterval = setInterval(fetchChapters, 2000);

    return () => {
      clearInterval(chapterInterval);
      if (progressInterval.current) {
        clearInterval(progressInterval.current);
      }
    };
  }, [id]);

  // Poll for progress when there are running tasks
  useEffect(() => {
    const runningChapters = chapters.filter(c => c.status === 'converting');
    if (runningChapters.length > 0 && !progressInterval.current) {
      progressInterval.current = setInterval(fetchTaskProgress, 1000);
    } else if (runningChapters.length === 0 && progressInterval.current) {
      clearInterval(progressInterval.current);
      progressInterval.current = null;
    }
    return () => {
      if (progressInterval.current) {
        clearInterval(progressInterval.current);
        progressInterval.current = null;
      }
    };
  }, [chapters]);

  const fetchBook = async () => {
    try {
      const res = await api.get(`/api/books/${id}`);
      setBook(res.data);
    } catch (err) {
      message.error('获取图书信息失败');
    }
  };

  const fetchChapters = async () => {
    try {
      const res = await api.get(`/api/books/${id}/chapters`);
      setChapters(res.data);
    } catch (err) {
      message.error('获取章节列表失败');
    }
  };

  const fetchPresets = async () => {
    try {
      const res = await api.get('/api/voice-presets');
      setPresets(res.data.items);
    } catch (err) {
      message.error('获取语音预设失败');
    }
  };

  const fetchTaskProgress = async () => {
    try {
      const tasksRes = await api.get('/api/tasks', { params: { book_id: id, status: 'running' } });
      const runningTasks = tasksRes.data.items;
      const progressMap = {};
      for (const task of runningTasks) {
        try {
          const progressRes = await api.get(`/api/tasks/${task.id}/progress`);
          progressMap[task.chapter_id] = progressRes.data;
        } catch (e) {}
      }
      setTaskProgress(progressMap);

      // Refresh chapters if any task completed
      if (Object.keys(progressMap).length === 0 && Object.keys(taskProgress).length > 0) {
        fetchChapters();
      }
    } catch (err) {}
  };

  const handleConvert = async (chapterIds = null) => {
    setLoading(true);
    try {
      const ids = chapterIds ? (Array.isArray(chapterIds) ? chapterIds : [chapterIds]) : null;
      await api.post('/api/tasks', {
        book_id: parseInt(id),
        chapter_ids: ids,
        voice_preset_id: selectedPreset,
      });
      message.success('任务已创建');

      // 延迟后刷新章节状态（等待任务开始执行）
      setTimeout(() => {
        fetchChapters();
      }, 500);
    } catch (err) {
      message.error('创建任务失败');
    }
    setLoading(false);
  };

  const handlePlay = (chapter) => {
    if (chapter.audio_path) {
      playAudio({
        url: `/api/audio/${id}/${chapter.id}/stream?t=${Date.now()}`,
        title: chapter.title,
        bookTitle: book?.title,
      });
    }
  };

  const handleDownloadChapter = (chapter) => {
    setDownloadingChapter(chapter.id);
    const url = `/api/audio/${id}/${chapter.id}`;
    // 使用隐藏iframe触发下载，不影响当前页面
    const iframe = document.createElement('iframe');
    iframe.style.display = 'none';
    iframe.src = url;
    document.body.appendChild(iframe);
    // 3秒后移除iframe并清除状态
    setTimeout(() => {
      document.body.removeChild(iframe);
      setDownloadingChapter(null);
    }, 3000);
  };

  const handleDownloadBook = () => {
    setDownloadingZip(true);
    const url = `/api/audio/${id}/zip`;
    // 使用隐藏iframe触发下载
    const iframe = document.createElement('iframe');
    iframe.style.display = 'none';
    iframe.src = url;
    document.body.appendChild(iframe);
    // 5秒后移除iframe并清除状态
    setTimeout(() => {
      document.body.removeChild(iframe);
      setDownloadingZip(false);
    }, 5000);
  };

  const formatElapsed = (seconds) => {
    if (!seconds) return '';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return mins > 0 ? `${mins}m${secs}s` : `${secs}s`;
  };

  const handleViewChapter = async (chapter) => {
    setViewChapter(chapter);
    setViewModalVisible(true);
    setViewLoading(true);
    try {
      const res = await api.get(`/api/chapters/${chapter.id}`);
      setViewContent(res.data.text_content || '');
    } catch (err) {
      message.error('获取章节内容失败');
      setViewContent('');
    }
    setViewLoading(false);
  };

  const handleCloseView = () => {
    setViewModalVisible(false);
    setViewChapter(null);
    setViewContent('');
  };

  const columns = [
    { title: '章节', dataIndex: 'chapter_number', width: 80 },
    { title: '标题', dataIndex: 'title', ellipsis: true },
    { title: '字数', dataIndex: 'word_count', width: 100 },
    {
      title: '状态',
      dataIndex: 'status',
      width: 200,
      render: (status, record) => {
        const statusMap = {
          pending: { color: 'default', text: '待转换' },
          queued: { color: 'warning', text: '排队中' },
          converting: { color: 'processing', text: '转换中' },
          completed: { color: 'success', text: '已完成' },
          failed: { color: 'error', text: '失败' },
          skipped: { color: 'warning', text: '跳过' },
        };
        const s = statusMap[status] || { color: 'default', text: status };

        // Show progress for converting status
        if (status === 'converting') {
          const progress = taskProgress[record.id];
          if (progress && progress.progress !== undefined) {
            return (
              <div style={{ minWidth: 150 }}>
                <Progress
                  percent={Math.round(progress.progress)}
                  size="small"
                  status="active"
                  format={(p) => `${p}%`}
                />
                <Tooltip title={progress.message}>
                  <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>
                    {formatElapsed(progress.elapsed) && `已用 ${formatElapsed(progress.elapsed)}`}
                  </div>
                </Tooltip>
              </div>
            );
          }
          return <Tag color="processing" icon={<SyncOutlined spin />}>转换中</Tag>;
        }

        return <Tag color={s.color}>{s.text}</Tag>;
      },
    },
    {
      title: '时长',
      dataIndex: 'audio_duration',
      width: 80,
      render: (d) => d ? `${d.toFixed(1)}s` : '-',
    },
    {
      title: '操作',
      width: 180,
      render: (_, record) => (
        <Space size={4}>
          <Tooltip title="查看内容">
            <Button
              size="small"
              type="link"
              icon={<EyeOutlined />}
              onClick={() => handleViewChapter(record)}
            />
          </Tooltip>
          {record.status === 'pending' && (
            <Tooltip title="转换">
              <Button
                size="small"
                type="link"
                icon={<AudioOutlined />}
                onClick={() => handleConvert(record.id)}
              />
            </Tooltip>
          )}
          {record.status === 'converting' && (
            <Tooltip title="转换中...">
              <Button size="small" type="link" icon={<ClockCircleOutlined />} disabled />
            </Tooltip>
          )}
          {record.status === 'completed' && (
            <>
              <Tooltip title="播放">
                <Button
                  size="small"
                  type="link"
                  icon={<PlayCircleOutlined />}
                  onClick={() => handlePlay(record)}
                />
              </Tooltip>
              <Tooltip title="下载">
                <Button
                  size="small"
                  type="link"
                  icon={<DownloadOutlined />}
                  onClick={() => handleDownloadChapter(record)}
                  loading={downloadingChapter === record.id}
                />
              </Tooltip>
              <Tooltip title="重新生成">
                <Button
                  size="small"
                  type="link"
                  icon={<ReloadOutlined />}
                  onClick={() => handleConvert(record.id)}
                />
              </Tooltip>
            </>
          )}
          {record.status === 'failed' && (
            <Tooltip title="重试">
              <Button
                size="small"
                type="link"
                icon={<ReloadOutlined />}
                onClick={() => handleConvert(record.id)}
              />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      {book && (
        <Card style={{ marginBottom: 16 }}>
          <Descriptions title="图书信息">
            <Descriptions.Item label="书名">{book.title}</Descriptions.Item>
            <Descriptions.Item label="作者">{book.author || '-'}</Descriptions.Item>
            <Descriptions.Item label="格式">{book.format}</Descriptions.Item>
            <Descriptions.Item label="章节数">{book.chapter_count}</Descriptions.Item>
            <Descriptions.Item label="状态">{book.status}</Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      <div style={{ marginBottom: 16, display: 'flex', gap: 16, alignItems: 'center' }}>
        <Select
          placeholder="选择语音预设"
          style={{ width: 200 }}
          value={selectedPreset}
          onChange={handlePresetChange}
          options={[
            { label: '随机', value: null },
            ...presets.map(p => ({ label: p.name, value: p.id }))
          ]}
        />
        <Button
          type="primary"
          icon={<AudioOutlined />}
          onClick={() => handleConvert()}
          loading={loading}
        >
          转换全部未完成章节
        </Button>
        <Button onClick={() => fetchChapters()}>刷新</Button>
        <Button
          icon={<DownloadOutlined />}
          onClick={handleDownloadBook}
          loading={downloadingZip}
          disabled={!chapters.some(c => c.status === 'completed')}
        >
          下载全部音频
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={chapters}
        rowKey="id"
        pagination={false}
      />

      <Modal
        title={viewChapter ? `第${viewChapter.chapter_number}章 ${viewChapter.title}` : '章节内容'}
        open={viewModalVisible}
        onCancel={handleCloseView}
        footer={[
          <Button key="close" onClick={handleCloseView}>
            关闭
          </Button>
        ]}
        width={800}
        styles={{ body: { maxHeight: '60vh', overflowY: 'auto' } }}
      >
        {viewLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>加载中...</div>
        ) : (
          <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8, fontSize: 14 }}>
            {viewContent || '无内容'}
          </div>
        )}
      </Modal>
    </div>
  );
}

export default BookDetail;
