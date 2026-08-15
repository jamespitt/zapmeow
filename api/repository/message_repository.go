package repository

import (
	"time"
	"zapmeow/api/model"
	"zapmeow/pkg/database"
)

type MessageRepository interface {
	CreateMessage(message *model.Message) error
	CreateMessages(messages *[]model.Message) error
	GetChatMessages(instanceID string, chatJID string) (*[]model.Message, error)
	GetMessagesByInstanceID(instanceID string, chatJID string, limit int, before *time.Time) (*[]model.Message, error)
	GetChatsByInstanceID(instanceID string) (*[]model.Message, map[string]int64, error)
	GetMessageByMessageID(instanceID string, messageID string) (*model.Message, error)
	CountChatMessages(instanceID string, chatJID string) (int64, error)
	DeleteMessagesByInstanceID(instanceID string) error
}

type messageRepository struct {
	database database.Database
}

func NewMessageRepository(database database.Database) *messageRepository {
	return &messageRepository{database: database}
}

func (repo *messageRepository) CreateMessage(message *model.Message) error {
	return repo.database.Client().Create(message).Error
}

func (repo *messageRepository) CreateMessages(messages *[]model.Message) error {
	return repo.database.Client().Create(messages).Error
}

func (repo *messageRepository) CountChatMessages(instanceID string, chatJID string) (int64, error) {
	var count int64
	if result := repo.database.Client().Model(&model.Message{}).Where("instance_id = ? AND chat_jid = ?", instanceID, chatJID).Count(&count); result.Error != nil {
		return 0, result.Error
	}
	return count, nil
}

func (repo *messageRepository) GetMessageByMessageID(instanceID string, messageID string) (*model.Message, error) {
	var message model.Message
	if result := repo.database.Client().Where("instance_id = ? AND message_id = ?", instanceID, messageID).First(&message); result.Error != nil {
		return nil, result.Error
	}
	return &message, nil
}

func (repo *messageRepository) GetChatMessages(instanceID string, chatJID string) (*[]model.Message, error) {
	var messages []model.Message
	if result := repo.database.Client().Where("instance_id = ? AND chat_jid = ?", instanceID, chatJID).Order("timestamp DESC").Find(&messages); result.Error != nil {
		return nil, result.Error
	}
	return &messages, nil
}

// GetMessagesByInstanceID returns messages for the instance, newest first.
// If chatJID is non-empty, only that chat's messages are returned. If before
// is non-nil, only messages strictly older than it are returned (for
// cursor-based pagination).
func (repo *messageRepository) GetMessagesByInstanceID(instanceID string, chatJID string, limit int, before *time.Time) (*[]model.Message, error) {
	var messages []model.Message
	query := repo.database.Client().Where("instance_id = ?", instanceID)
	if chatJID != "" {
		query = query.Where("chat_jid = ?", chatJID)
	}
	if before != nil {
		query = query.Where("timestamp < ?", *before)
	}
	if result := query.Order("timestamp DESC").Limit(limit).Find(&messages); result.Error != nil {
		return nil, result.Error
	}
	return &messages, nil
}

// GetChatsByInstanceID returns, for each chat the instance has messages in,
// the most recent message plus a message-count map keyed by chat JID. Chats
// are not ordered here; callers order by the returned messages' timestamps.
func (repo *messageRepository) GetChatsByInstanceID(instanceID string) (*[]model.Message, map[string]int64, error) {
	var latest []model.Message
	// SQLite window function: rank each chat's messages newest-first (ties
	// broken by id) and keep only the top row per chat.
	sql := `
		SELECT id, created_at, updated_at, deleted_at, sender_jid, chat_jid, instance_id,
		       message_id, timestamp, body, media_type, mimetype, media_path, from_me
		FROM (
			SELECT m.*, ROW_NUMBER() OVER (
				PARTITION BY chat_jid ORDER BY timestamp DESC, id DESC
			) AS rn
			FROM messages m
			WHERE instance_id = ?
		) ranked
		WHERE rn = 1
		ORDER BY timestamp DESC
	`
	if result := repo.database.Client().Raw(sql, instanceID).Scan(&latest); result.Error != nil {
		return nil, nil, result.Error
	}

	var counts []struct {
		ChatJID string
		Count   int64
	}
	if result := repo.database.Client().Model(&model.Message{}).
		Select("chat_jid, COUNT(*) as count").
		Where("instance_id = ?", instanceID).
		Group("chat_jid").
		Scan(&counts); result.Error != nil {
		return nil, nil, result.Error
	}

	countByChat := make(map[string]int64, len(counts))
	for _, c := range counts {
		countByChat[c.ChatJID] = c.Count
	}

	return &latest, countByChat, nil
}

func (repo *messageRepository) DeleteMessagesByInstanceID(instanceID string) error {
	if result := repo.database.Client().Where("instance_id = ?", instanceID).Unscoped().Delete(&model.Message{}); result.Error != nil {
		return result.Error
	}
	return nil
}
