import React, { useState, useEffect } from 'react';
import { Table, Button, Select, Tag, message, Space, Tooltip } from 'antd';
import { ReloadOutlined, DeleteOutlined, PlayCircleOutlined, AudioOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import api from '../api';

function TaskList() {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState(null);
  const [bookFilter, setBookFilter] = useState(null);
  const [books, setBooks] = useState([]);
  const [chapters, setChapters] = useState({});
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });
  const navigate = useNavigate();

  useEffect(() => {
    fetchTasks();
    fetchBooks();
    const interval = setInterval(fetchTasks, 3000);
    return () => clearInterval(interval);
  }, [statusFilter, bookFilter, pagination.current]);

  const fetchTasks = async () => {
    try {
      const params = {
        page: pagination.current,
        page_size: pagination.pageSize,
      };
      if (statusFilter) params.status = statusFilter;
      if (bookFilter) params.book_id = bookFilter;
      const res = await api.get('/api/tasks', { params });
      // 增量更新：仅替换实际变化的任务
      setTasks(prev => {
        const prevMap = new Map(prev.map(t => [t.id, t]));
        return res.data.items.map(item => {
          const old = prevMap.get(item.id);
          if (old
            && old.status === item.status
            && old.progress === item.progress
            && !old.error_message
          ) {
            return old;
          }
          return item;
        });
      });
      setPagination(prev => ({ ...prev, total: res.data.total }));

      // Fetch chapter info for each task
      const chapterIds = [...new Set(res.data.items.map(t => t.chapter_id))];
      const chaptersMap = {};
      for (const chId of chapterIds) {
        try {
          const chRes = await api.get(`/api/chapters/${chId}`);
          chaptersMap[chId] = chRes.data;
        } catch (e) {}
      }
      setChapters(chaptersMap);
    } catch (err) {
      message.error('获取任务列表失败');
    }
    setLoading(false);
  };

  const handlePageChange = (page, pageSize) => {
    setPagination(prev => ({ ...prev, current: page, pageSize }));
  };

  const fetchBooks = async () => {
    try {
      const res = await api.get('/api/books');
      setBooks(res.data.items);
    } catch (err) {
      message.error('获取图书列表失败');
    }
  };

  const handleRetry = async (taskId) => {
    try {
      await api.post(`/api/tasks/${taskId}/retry`);
      message.success('重试成功');
      fetchTasks();
    } catch (err) {
      message.error('重试失败');
    }
  };

  const handleRetryAllFailed = async () => {
    const failedTasks = tasks.filter(t => t.status === 'failed');
    if (failedTasks.length === 0) return;
    let success = 0;
    for (const task of failedTasks) {
      try {
        await api.post(`/api/tasks/${task.id}/retry`);
        success++;
      } catch (e) {}
    }
    message.success(`已重试 ${success}/${failedTasks.length} 个任务`);
    fetchTasks();
  };

  const handleCancel = async (taskId) => {
    try {
      await api.delete(`/api/tasks/${taskId}`);
      message.success('取消成功');
      fetchTasks();
    } catch (err) {
      message.error('取消失败');
    }
  };

  const statusMap = {
    pending: { color: 'default', text: '待处理' },
    queued: { color: 'warning', text: '排队中' },
    running: { color: 'processing', text: '运行中' },
    completed: { color: 'success', text: '已完成' },
    failed: { color: 'error', text: '失败' },
    skipped: { color: 'warning', text: '跳过' },
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    {
      title: '图书',
      dataIndex: 'book_id',
      width: 150,
      render: (bookId) => {
        const book = books.find(b => b.id === bookId);
        return book?.title || bookId;
      },
    },
    {
      title: '章节',
      dataIndex: 'chapter_id',
      width: 200,
      render: (chapterId) => {
        const chapter = chapters[chapterId];
        if (chapter) {
          return (
            <Tooltip title={`第${chapter.chapter_number}章 - ${chapter.title}`}>
              <span>第{chapter.chapter_number}章: {chapter.title?.substring(0, 15)}{chapter.title?.length > 15 ? '...' : ''}</span>
            </Tooltip>
          );
        }
        return `章节 ${chapterId}`;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status) => {
        const s = statusMap[status] || { color: 'default', text: status };
        return <Tag color={s.color}>{s.text}</Tag>;
      },
    },
    {
      title: '错误信息',
      dataIndex: 'error_message',
      ellipsis: true,
      render: (msg) => msg ? <Tooltip title={msg}><span style={{ color: '#ff4d4f' }}>{msg.substring(0, 30)}...</span></Tooltip> : '-',
    },
    {
      title: '耗时',
      width: 100,
      render: (_, record) => {
        if (record.started_at && record.finished_at) {
          const start = new Date(record.started_at + 'Z');
          const end = new Date(record.finished_at + 'Z');
          const seconds = Math.round((end - start) / 1000);
          if (seconds < 60) return `${seconds}秒`;
          return `${Math.floor(seconds / 60)}分${seconds % 60}秒`;
        }
        if (record.started_at && record.status === 'running') {
          const start = new Date(record.started_at + 'Z');
          const now = new Date();
          const seconds = Math.round((now - start) / 1000);
          return `${seconds}秒...`;
        }
        return '-';
      },
    },
    {
      title: '操作',
      width: 200,
      render: (_, record) => (
        <Space>
          {(record.status === 'pending' || record.status === 'queued') && (
            <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleCancel(record.id)}>
              取消
            </Button>
          )}
          {record.status === 'running' && (
            <Button size="small" disabled icon={<AudioOutlined />}>
              转换中
            </Button>
          )}
          {record.status === 'completed' && (
            <Button
              size="small"
              type="link"
              icon={<ReloadOutlined />}
              onClick={() => handleRetry(record.id)}
            >
              重新生成
            </Button>
          )}
          {record.status === 'failed' && (
            <>
              <Button size="small" icon={<ReloadOutlined />} onClick={() => handleRetry(record.id)}>
                重试
              </Button>
              <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleCancel(record.id)}>
                删除
              </Button>
            </>
          )}
          {record.status === 'skipped' && (
            <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleCancel(record.id)}>
              删除
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', gap: 16 }}>
        <Select
          placeholder="按状态筛选"
          style={{ width: 150 }}
          value={statusFilter}
          onChange={(value) => {
            setStatusFilter(value);
            setPagination(prev => ({ ...prev, current: 1 }));
          }}
          allowClear
          options={[
            { label: '全部', value: null },
            { label: '待处理', value: 'pending' },
            { label: '排队中', value: 'queued' },
            { label: '运行中', value: 'running' },
            { label: '已完成', value: 'completed' },
            { label: '失败', value: 'failed' },
            { label: '跳过', value: 'skipped' },
          ]}
        />
        <Select
          placeholder="按图书筛选"
          style={{ width: 200 }}
          value={bookFilter}
          onChange={(value) => {
            setBookFilter(value);
            setPagination(prev => ({ ...prev, current: 1 }));
          }}
          allowClear
          options={books.map(b => ({ label: b.title, value: b.id }))}
        />
        <Button onClick={fetchTasks}>刷新</Button>
        {tasks.filter(t => t.status === 'failed').length > 0 && (
          <Button
            icon={<ReloadOutlined />}
            onClick={handleRetryAllFailed}
          >
            重试本页失败 ({tasks.filter(t => t.status === 'failed').length})
          </Button>
        )}
      </div>

      <Table
        columns={columns}
        dataSource={tasks}
        rowKey="id"
        pagination={{
          current: pagination.current,
          pageSize: pagination.pageSize,
          total: pagination.total,
          onChange: handlePageChange,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条`,
        }}
      />
    </div>
  );
}

export default TaskList;
