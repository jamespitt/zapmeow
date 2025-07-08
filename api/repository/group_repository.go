package repository

import (
	"zapmeow/api/model"
	"zapmeow/pkg/database"

	"gorm.io/gorm"
)

type GroupRepository interface {
	SaveGroup(group *model.Group) error
	GetGroupByJID(jid string) (*model.Group, error)
}

type groupRepository struct {
	database database.Database
}

func NewGroupRepository(database database.Database) *groupRepository {
	return &groupRepository{database: database}
}

func (repo *groupRepository) SaveGroup(group *model.Group) error {
	// GORM's Save method handles both creation and updates.
	// If the primary key is zero, it creates; otherwise, it updates.
	return repo.database.Client().Save(group).Error
}

func (repo *groupRepository) GetGroupByJID(jid string) (*model.Group, error) {
	var group model.Group
	result := repo.database.Client().Where("jid = ?", jid).First(&group)
	if result.Error != nil {
		if result.Error == gorm.ErrRecordNotFound {
			return nil, nil // Return nil, nil for not found, so service layer can handle it
		}
		return nil, result.Error // Return actual error for other issues
	}
	return &group, nil
}
