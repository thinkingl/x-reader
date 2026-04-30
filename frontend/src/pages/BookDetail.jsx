import React, { useState, useEffect, useContext, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { Table, Button, Select, message, Space, Tag, Card, Descriptions, Tooltip, Progress, Modal, Input, Form, Popconfirm } from 'antd';
import { PlayCircleOutlined, ReloadOutlined, AudioOutlined, SyncOutlined, ClockCircleOutlined, DownloadOutlined, EyeOutlined, EditOutlined, SaveOutlined, DeleteOutlined, RedoOutlined } from '@ant-design/icons';
import api from '../api';
import { AudioContext } from '../components/AudioPlayer';

function BookDetail() {
  const { id } = useParams();
  const [book, setBook] = useState(null);
  const [chapters, setChapters] = useState([]);
  const [totalChapters, setTotalChapters] = useState(0);
  const [tablePage, setTablePage] = useState(1);
  const [tablePageSize, setTablePageSize] = useState(50);
  const [hasRunningChapters, setHasRunningChapters] = useState(false);
  const [presets, setPresets] = useState([]);
  const [selectedPreset, setSelectedPreset] = useState(() => {
    const saved = localStorage.getItem('selectedPreset');
    return saved ? parseInt(saved) : null;
  });
  const [loading, setLoading] = useState(false);
  const [downloadingZip, setDownloadingZip] = useState(false);
  const [downloadingChapter, setDownloadingChapter] = useState(null);
  const [reparsing, setReparsing] = useState(false);
  const [taskProgress, setTaskProgress] = useState({});
  const { playAudio } = useContext(AudioContext);
  const progressInterval = useRef(null);
  const pollInterval = useRef(null);
  
  // 图书编辑
  const [editBookModalVisible, setEditBookModalVisible] = useState(false);
  const [editBookForm] = Form.useForm();
  const [editBookLoading, setEditBookLoading] = useState(false);

  // 章节内容查看/编辑
  const [viewModalVisible, setViewModalVisible] = useState(false);
  const [viewChapter, setViewChapter] = useState(null);
  const [viewContent, setViewContent] = useState('');
  const [viewLoading, setViewLoading] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [isEditingContent, setIsEditingContent] = useState(false);
  const [saveContentLoading, setSaveContentLoading] = useState(false);

  const handlePresetChange = (value) => {
    setSelectedPreset(value);
    if (value === null) {
      localStorage.removeItem('selectedPreset');
    } else {
      localStorage.setItem('selectedPreset', value);
    }
  };

  const handleEditBook = () => {
    editBookForm.setFieldsValue({ title: book.title, author: book.author });
    setEditBookModalVisible(true);
  };

  const handleSaveBook = async () => {
    try {
      const values = await editBookForm.validateFields();
      setEditBookLoading(true);
      await api.patch(`/api/books/${id}`, values);
      message.success('图书信息已更新');
      setEditBookModalVisible(false);
      fetchBook();
    } catch (err) {
      if (err.response) message.error('保存失败');
    }
    setEditBookLoading(false);
  };

  const handleViewChapter = async (chapter) => {
    setViewChapter(chapter);
    setViewModalVisible(true);
    setIsEditingContent(false);
    setViewLoading(true);
    try {
      const res = await api.get(`/api/chapters/${chapter.id}`);
      const content = res.data.text_content || '';
      setViewContent(content);
      setEditContent(content);
    } catch (err) {
      message.error('获取章节内容失败');
      setViewContent('');
      setEditContent('');
    }
    setViewLoading(false);
  };

  const handleSaveChapterContent = async () => {
    if (!viewChapter) return;
    setSaveContentLoading(true);
    try {
      await api.patch(`/api/chapters/${viewChapter.id}`, { text_content: editContent });
      message.success('章节内容已更新');
      setViewContent(editContent);
      setIsEditingContent(false);
      fetchChapters(1);
    } catch (err) {
      message.error('保存失败');
    }
    setSaveContentLoading(false);
  };

  const handleCloseView = () => {
    setViewModalVisible(false);
    setViewChapter(null);
    setViewContent('');
    setEditContent('');
    setIsEditingContent(false);
  };

  useEffect(() => {
    fetchBook();
    fetchChapters(1);
    fetchPresets();

    return () => {
      if (pollInterval.current) clearInterval(pollInterval.current);
      if (progressInterval.current) clearInterval(progressInterval.current);
    };
  }, [id]);

  // 智能轮询：有 pending/queued/running 状态章节时才每 2 秒刷新
  useEffect(() => {
    const activeChapters = chapters.filter(
      c => c.status === 'pending' || c.status === 'queued' || c.status === 'converting'
    );
    const hasActive = activeChapters.length > 0;

    if (hasActive && !pollInterval.current) {
      pollInterval.current = setInterval(() => fetchChapters(), 2000);
    } else if (!hasActive && pollInterval.current) {
      clearInterval(pollInterval.current);
      pollInterval.current = null;
    }
    if (hasActive !== hasRunningChapters) {
      setHasRunningChapters(hasActive);
    }

    return () => {
      if (pollInterval.current) {
        clearInterval(pollInterval.current);
        pollInterval.current = null;
      }
    };
  }, [chapters]);

  // Poll for progress when there are converting chapters
  useEffect(() => {
    const converting = chapters.filter(c => c.status === 'converting');
    if (converting.length > 0 && !progressInterval.current) {
      progressInterval.current = setInterval(fetchTaskProgress, 1000);
    } else if (converting.length === 0 && progressInterval.current) {
      clearInterval(progressInterval.current);
      progressInterval.current = null;
    }
    return () => {
      if (progressInterval.current) {
        clearInterval(progressInterval.current);
        progressInterval.current = null;
      }
    };
  }, [hasRunningChapters, chapters]);

  const fetchBook = async () => {
    try {
      const res = await api.get(`/api/books/${id}`);
      setBook(res.data);
    } catch (err) {
      message.error('获取图书信息失败');
    }
  };

  const fetchChapters = async (page = tablePage, pageSize = tablePageSize) => {
    try {
      const res = await api.get(`/api/books/${id}/chapters`, {
        params: { page, page_size: pageSize },
      });
      setTotalChapters(res.data.total);
      // 增量更新：仅替换实际变化的章节，未变化的保留旧引用以避免重渲染
      setChapters(prev => {
        const prevMap = new Map(prev.map(c => [c.id, c]));
        return res.data.items.map(item => {
          const old = prevMap.get(item.id);
          if (old
            && old.status === item.status
            && old.audio_path === item.audio_path
            && old.audio_duration === item.audio_duration
            && old.word_count === item.word_count
          ) {
            return old;
          }
          return item;
        });
      });
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
        fetchChapters(1);
      }
    } catch (err) {}
  };

  const handleConvert = async (chapterIds = null, force = false) => {
    setLoading(true);
    try {
      const ids = chapterIds ? (Array.isArray(chapterIds) ? chapterIds : [chapterIds]) : null;
      await api.post('/api/tasks', {
        book_id: parseInt(id),
        chapter_ids: ids,
        voice_preset_id: selectedPreset,
        force,
      });
      message.success('任务已创建');

      // 延迟后刷新章节状态（等待任务开始执行）
      setTimeout(() => {
        setTablePage(1);
        fetchChapters(1);
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

  const handleDeleteChapter = async (chapter) => {
    try {
      await api.delete(`/api/chapters/${chapter.id}`);
      message.success('章节已删除');
      fetchBook();
      setTablePage(1);
      fetchChapters(1);
    } catch (err) {
      message.error('删除失败');
    }
  };

  const handleReparse = async () => {
    setReparsing(true);
    try {
      const res = await api.post(`/api/books/${id}/reparse`);
      message.success(res.data.message);
      fetchBook();
      setTablePage(1);
      fetchChapters(1);
    } catch (err) {
      message.error('重新解析失败: ' + (err.response?.data?.detail || err.message));
    }
    setReparsing(false);
  };

  const formatElapsed = (seconds) => {
    if (!seconds) return '';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return mins > 0 ? `${mins}m${secs}s` : `${secs}s`;
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
      width: 200,
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
                  onClick={() => handleConvert(record.id, true)}
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
                onClick={() => handleConvert(record.id, true)}
              />
            </Tooltip>
          )}
          <Popconfirm
            title="确定删除此章节？"
            description="删除后相关任务和音频也会被删除"
            onConfirm={() => handleDeleteChapter(record)}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Tooltip title="删除">
              <Button size="small" type="link" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {book && (
        <Card style={{ marginBottom: 16 }}>
          <Descriptions title={
            <Space>
              图书信息
              <Button size="small" icon={<EditOutlined />} onClick={handleEditBook}>编辑</Button>
            </Space>
          }>
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
        <Button onClick={() => { setTablePage(1); fetchChapters(1); }}>刷新</Button>
        <Popconfirm
          title="确定重新解析？"
          description="重新解析将删除所有章节、任务和音频，从电子书文件重新提取文本"
          onConfirm={handleReparse}
          okText="确定"
          cancelText="取消"
          okButtonProps={{ danger: true }}
        >
          <Button icon={<RedoOutlined />} loading={reparsing}>重新解析</Button>
        </Popconfirm>
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
        pagination={{
          current: tablePage,
          pageSize: tablePageSize,
          total: totalChapters,
          showSizeChanger: true,
          pageSizeOptions: ['20', '50', '100', '200'],
          showTotal: (total, range) => `${range[0]}-${range[1]} / ${total} 章`,
          onChange: (page, pageSize) => {
            setTablePage(page);
            setTablePageSize(pageSize);
            fetchChapters(page, pageSize);
          },
        }}
      />

      <Modal
        title={viewChapter ? `第${viewChapter.chapter_number}章 ${viewChapter.title}` : '章节内容'}
        open={viewModalVisible}
        onCancel={handleCloseView}
        footer={[
          isEditingContent ? (
            <Space key="edit">
              <Button onClick={() => { setIsEditingContent(false); setEditContent(viewContent); }}>取消</Button>
              <Button type="primary" icon={<SaveOutlined />} onClick={handleSaveChapterContent} loading={saveContentLoading}>保存</Button>
            </Space>
          ) : (
            <Space key="view">
              <Button icon={<EditOutlined />} onClick={() => setIsEditingContent(true)}>编辑</Button>
              <Button onClick={handleCloseView}>关闭</Button>
            </Space>
          )
        ]}
        width={800}
        styles={{ body: { maxHeight: '60vh', overflowY: 'auto' } }}
      >
        {viewLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>加载中...</div>
        ) : isEditingContent ? (
          <Input.TextArea
            value={editContent}
            onChange={(e) => setEditContent(e.target.value)}
            autoSize={{ minRows: 15, maxRows: 30 }}
            style={{ fontSize: 14, lineHeight: 1.8 }}
          />
        ) : (
          <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8, fontSize: 14 }}>
            {viewContent || '无内容'}
          </div>
        )}
      </Modal>

      <Modal
        title="编辑图书信息"
        open={editBookModalVisible}
        onCancel={() => setEditBookModalVisible(false)}
        onOk={handleSaveBook}
        confirmLoading={editBookLoading}
      >
        <Form form={editBookForm} layout="vertical">
          <Form.Item label="书名" name="title" rules={[{ required: true, message: '请输入书名' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="作者" name="author">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default BookDetail;
