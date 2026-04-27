import React, { useState, useEffect } from 'react';
import { Table, Button, Upload, Modal, Input, message, Space, Tag } from 'antd';
import { UploadOutlined, DeleteOutlined, EyeOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import api from '../api';

function BookList() {
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadModalVisible, setUploadModalVisible] = useState(false);
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadAuthor, setUploadAuthor] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    fetchBooks();
  }, []);

  const fetchBooks = async () => {
    setLoading(true);
    try {
      const res = await api.get('/api/books');
      setBooks(res.data.items);
    } catch (err) {
      message.error('获取图书列表失败');
    }
    setLoading(false);
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`/api/books/${id}`);
      message.success('删除成功');
      fetchBooks();
    } catch (err) {
      message.error('删除失败');
    }
  };

  const handleUpload = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    if (uploadTitle) formData.append('title', uploadTitle);
    if (uploadAuthor) formData.append('author', uploadAuthor);

    try {
      await api.post('/api/books/upload', formData);
      message.success('上传成功');
      setUploadModalVisible(false);
      setUploadTitle('');
      setUploadAuthor('');
      fetchBooks();
    } catch (err) {
      message.error('上传失败');
    }
    return false;
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '书名', dataIndex: 'title' },
    { title: '作者', dataIndex: 'author' },
    { title: '格式', dataIndex: 'format', width: 80 },
    { title: '章节数', dataIndex: 'chapter_count', width: 80 },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status) => {
        const colorMap = {
          uploaded: 'default',
          parsed: 'blue',
          converting: 'orange',
          completed: 'green',
        };
        return <Tag color={colorMap[status]}>{status}</Tag>;
      },
    },
    {
      title: '操作',
      width: 200,
      render: (_, record) => (
        <Space>
          <Button icon={<EyeOutlined />} onClick={() => navigate(`/books/${record.id}`)}>
            查看
          </Button>
          <Button danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)}>
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" onClick={() => setUploadModalVisible(true)}>
          上传电子书
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={books}
        rowKey="id"
        loading={loading}
      />

      <Modal
        title="上传电子书"
        open={uploadModalVisible}
        onCancel={() => setUploadModalVisible(false)}
        footer={null}
      >
        <Input
          placeholder="书名（可选）"
          value={uploadTitle}
          onChange={(e) => setUploadTitle(e.target.value)}
          style={{ marginBottom: 16 }}
        />
        <Input
          placeholder="作者（可选）"
          value={uploadAuthor}
          onChange={(e) => setUploadAuthor(e.target.value)}
          style={{ marginBottom: 16 }}
        />
        <Upload
          accept=".epub,.pdf,.txt,.mobi"
          showUploadList={false}
          beforeUpload={handleUpload}
        >
          <Button icon={<UploadOutlined />}>选择文件</Button>
        </Upload>
      </Modal>
    </div>
  );
}

export default BookList;
