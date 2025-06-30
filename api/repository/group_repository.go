package repository

import (
	"zapmeow/api/model"
	"zapmeow/pkg/database"

	"gorm.io/gorm"
)

type GroupRepository interface {
	CreateGroup(group *model.Group) error
	GetGroupByJID(jid string) (*model.Group, error)
}

type groupRepository struct {
	database database.Database
}

func NewGroupRepository(database database.Database) *groupRepository {
	return &groupRepository{database: database}
}

func (repo *groupRepository) CreateGroup(group *model.Group) error {
	return repo.database.Client().Create(group).Error
}

func (repo *groupRepository) GetGroupByJID(jid string) (*model.Group, error) {
	var group model.Group
	result := repo.database.Client().Where("jid = ?", jid).First(&group)
	if result.Error != nil {
		if result.Error != gorm.ErrRecordNotFound {
			return nil, result.Error
		}
		return nil, nil
	}
	return &group, nil
}
